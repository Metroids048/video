"""HyperFrames motion rendering, deterministic fallback, and FFmpeg composition."""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from avs.freshness import is_stale
from avs.timeline.models import Clip, Timeline

logger = logging.getLogger(__name__)

SUPPORTED_COMPONENTS = {"HookTitle", "InfoCard", "EndCard"}


@dataclass
class MotionRenderResult:
    output_path: Path | None
    manifest_path: Path
    rendered: list[Path] = field(default_factory=list)
    fallbacks: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _run(
    command: list[str], *, cwd: Path, env: dict[str, str], timeout: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _browser_environment(env: dict[str, str] | None = None) -> dict[str, str]:
    result = dict(env or os.environ)
    if result.get("HYPERFRAMES_BROWSER_PATH"):
        return result
    if os.name == "nt":
        candidates = (
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        )
        for candidate in candidates:
            if candidate.is_file():
                result["HYPERFRAMES_BROWSER_PATH"] = str(candidate)
                break
    return result


def _hyperframes_command(project_root: Path) -> list[str] | None:
    cli = project_root / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
    node = shutil.which("node")
    if not node or not cli.is_file():
        return None
    return [node, str(cli)]


def _write_log(path: Path, command: list[str], result: subprocess.CompletedProcess[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"$ {' '.join(command)}\n")
        if result.stdout:
            handle.write(result.stdout.rstrip() + "\n")
        if result.stderr:
            handle.write(result.stderr.rstrip() + "\n")
        handle.write(f"exit={result.returncode}\n\n")


def _valid_video(path: Path, *, require_audio: bool = False) -> bool:
    if not path.is_file() or path.stat().st_size == 0 or not shutil.which("ffprobe"):
        return False
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if probe.returncode != 0:
        return False
    try:
        streams = json.loads(probe.stdout).get("streams", [])
    except json.JSONDecodeError:
        return False
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    return bool(
        video
        and int(video.get("width", 0)) == 1080
        and int(video.get("height", 0)) == 1920
        and video.get("codec_name") == "h264"
        and (not require_audio or (audio and audio.get("codec_name") == "aac"))
    )


def _component_variables(template: str, clip: Clip) -> dict[str, str]:
    style = clip.style or {}
    text = clip.text or ""
    if template == "HookTitle":
        return {"title": text or "视频开场", "subtitle": str(style.get("subtitle") or "")}
    if template == "InfoCard":
        return {
            "label": str(style.get("label") or "核心要点"),
            "heading": text or "关键信息",
            "content": str(style.get("content") or ""),
        }
    return {"message": text or "感谢观看", "action": str(style.get("action") or "")}


def try_render_hyperframes(
    project_root: Path,
    component_path: Path,
    output_path: Path,
    props: dict[str, Any] | None = None,
    timeout: int = 180,
    log_path: Path | None = None,
) -> tuple[bool, str | None]:
    """Lint and render one component. Returns success and a warning message."""
    base_command = _hyperframes_command(project_root)
    if base_command is None:
        return False, "项目锁定的 HyperFrames CLI 或 Node.js 不可用"
    env = _browser_environment()
    log_path = log_path or project_root / "logs" / "hyperframes-render.log"
    try:
        lint_command = [*base_command, "lint", str(component_path), "--json"]
        lint_result = _run(lint_command, cwd=project_root, env=env, timeout=60)
        _write_log(log_path, lint_command, lint_result)
        if lint_result.returncode != 0:
            return False, f"{component_path.name} lint 失败"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        render_command = [
            *base_command,
            "render",
            str(component_path),
            "--output",
            str(output_path),
            "--quality",
            "standard",
            "--workers",
            "1",
        ]
        if props:
            render_command.extend(["--variables", json.dumps(props, ensure_ascii=False)])
        render_result = _run(render_command, cwd=project_root, env=env, timeout=timeout)
        _write_log(log_path, render_command, render_result)
        if render_result.returncode != 0:
            return False, f"{component_path.name} render 失败 (exit {render_result.returncode})"
    except subprocess.TimeoutExpired:
        return False, f"{component_path.name} render 超时 ({timeout}s)"
    except OSError as exc:
        return False, f"{component_path.name} render 异常: {exc}"
    if not _valid_video(output_path):
        return False, f"{component_path.name} 输出缺失或无法解码"
    return True, None


def render_static_fallback(
    component_type: str,
    props: dict[str, Any],
    output_path: Path,
    *,
    duration: float,
) -> None:
    """Generate a decodable static card without modifying the base rough cut."""
    text = str(props.get("title") or props.get("heading") or props.get("message") or component_type)
    escaped = text.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:")
    font = Path(r"C:\Windows\Fonts\msyh.ttc")
    font_filter = ""
    if font.is_file():
        font_filter = "fontfile='C\\:/Windows/Fonts/msyh.ttc':"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=#17232d:s=1080x1920:r=30:d={duration}",
        "-vf", (
            f"drawtext={font_filter}text='{escaped}':fontcolor=white:fontsize=56:"
            "x=(w-text_w)/2:y=(h-text_h)/2"
        ),
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-an", str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=90)
    if result.returncode != 0 or not _valid_video(output_path):
        raise RuntimeError(f"FFmpeg 静态卡片降级失败: {(result.stderr or '')[-300:]}")


def _compose_motion(base_video: Path, clips: list[tuple[Clip, Path]], output_path: Path) -> None:
    if not clips:
        return
    command = ["ffmpeg", "-y", "-i", str(base_video)]
    for _, path in clips:
        command.extend(["-i", str(path)])
    filters: list[str] = []
    current = "0:v"
    for index, (clip, _) in enumerate(clips, start=1):
        prepared = f"motion{index}"
        output = f"base{index}"
        filters.append(
            f"[{index}:v]setpts=PTS-STARTPTS+{clip.start}/TB,scale=1080:1920[{prepared}]",
        )
        filters.append(
            f"[{current}][{prepared}]overlay=0:0:eof_action=pass:"
            f"enable='between(t,{clip.start},{clip.end})'[{output}]",
        )
        current = output
    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", f"[{current}]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy", "-movflags", "+faststart", str(output_path),
    ])
    result = subprocess.run(command, capture_output=True, text=True, timeout=300)
    if result.returncode != 0 or not _valid_video(output_path, require_audio=True):
        raise RuntimeError(f"动效合成失败: {(result.stderr or '')[-500:]}")
    decode = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(output_path), "-f", "null", "-"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if decode.returncode != 0:
        raise RuntimeError(f"动效合成产物无法完整解码: {decode.stderr[-300:]}")


def render_motion_graphics(
    project_root: Path,
    ep_dir: Path,
    timeline: Timeline,
    *,
    force: bool = False,
    timeout: int = 180,
    base_video: Path | None = None,
    output_path: Path | None = None,
    write_manifest: bool = True,
) -> MotionRenderResult:
    """Render graphic-track clips, fall back per clip, and compose over the rough cut."""
    output_dir = ep_dir / "delivery" / "motion-graphics"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = ep_dir / "work" / "motion-manifest.json"
    timeline_path = ep_dir / "work" / "timeline.json"
    result = MotionRenderResult(output_path=None, manifest_path=manifest_path)
    graphic_track = timeline.get_track("graphic")
    entries: list[dict[str, Any]] = []
    composed: list[tuple[Clip, Path]] = []
    log_path = project_root / "logs" / f"hyperframes-render-{timeline.episode_id}.log"

    for clip in graphic_track.clips if graphic_track else []:
        template = str((clip.style or {}).get("motion_template") or "")
        if template not in SUPPORTED_COMPONENTS:
            unsupported_warning = f"{clip.clip_id}: 不支持的 motion_template {template!r}"
            result.warnings.append(unsupported_warning)
            entries.append({
                "clip_id": clip.clip_id, "template": template, "start": clip.start,
                "duration": clip.duration, "status": "skipped", "output": None,
                "warning": unsupported_warning,
            })
            continue
        output = output_dir / f"{clip.clip_id}.mp4"
        props = _component_variables(template, clip)
        status = "rendered"
        warning: str | None = None
        # 时间线更新后必须重渲：clip 的文案/时长变了，旧 mp4 依然"可解码"。
        if force or is_stale(output, [timeline_path]) or not _valid_video(output):
            success, warning = try_render_hyperframes(
                project_root,
                project_root / "renderers" / "hyperframes" / "components" / template,
                output,
                props,
                timeout,
                log_path,
            )
            if not success:
                status = "fallback"
                result.warnings.append(f"{clip.clip_id}: {warning}")
                render_static_fallback(template, props, output, duration=clip.duration)
        if status == "rendered":
            result.rendered.append(output)
        else:
            result.fallbacks.append(output)
        composed.append((clip, output))
        entries.append({
            "clip_id": clip.clip_id, "template": template, "start": clip.start,
            "duration": clip.duration, "status": status,
            "output": output.relative_to(ep_dir).as_posix(), "warning": warning,
        })

    selected_base = base_video or ep_dir / "renders" / "preview-with-captions.mp4"
    if composed and selected_base.is_file():
        motion_output = output_path or ep_dir / "renders" / "preview-with-motion.mp4"
        # 合成产物同时依赖底片与全部动效片段，任一更新都必须重新合成。
        composite_sources = [selected_base, timeline_path, *(path for _, path in composed)]
        if force or is_stale(motion_output, composite_sources) or not _valid_video(
            motion_output, require_audio=True,
        ):
            _compose_motion(selected_base, composed, motion_output)
        result.output_path = motion_output
    elif composed:
        result.warnings.append("基础粗剪不存在，已保留独立动效片段但未合成")

    payload = {
        "episode_id": timeline.episode_id,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "clips": entries,
        "composite_output": (
            result.output_path.relative_to(ep_dir).as_posix() if result.output_path else None
        ),
    }
    schema_path = project_root / "schemas" / "motion-manifest.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(
        schema, format_checker=jsonschema.FormatChecker(),
    ).validate(payload)
    if write_manifest:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
