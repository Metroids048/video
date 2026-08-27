"""Pinned production backend adapters for publishable video types."""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

MPT_VERSION = "1.2.7"
MPT_RUNTIME_RELATIVE = Path(".runtime") / "moneyprinterturbo"
_VIDEO_FILE = re.compile(r"^VIDEO_FILE=(?P<path>.+)$", re.MULTILINE)


class ProductionBackendError(RuntimeError):
    """A pinned production backend could not produce a candidate."""


@dataclass(frozen=True)
class MPTRequest:
    script: Path
    materials: Path
    audio: Path
    runtime: Path


def _project_root(ep_dir: Path) -> Path:
    for candidate in (ep_dir, *ep_dir.parents):
        if (candidate / "config" / "production-backends.yaml").is_file():
            return candidate
    raise ProductionBackendError("无法定位 config/production-backends.yaml")


def build_mpt_request(ep_dir: Path) -> MPTRequest:
    root = _project_root(ep_dir)
    script_candidates = (
        ep_dir / "work" / "content" / "script.md",
        ep_dir / "work" / "content" / "approved-script.md",
    )
    script = next((path for path in script_candidates if path.is_file()), None)
    materials = ep_dir / "work" / "prepared"
    audio_candidates = (
        ep_dir / "work" / "final-narration.mp3",
        ep_dir / "work" / "audio" / "final-narration.mp3",
        ep_dir / "work" / "narration.mp3",
    )
    audio = next((path for path in audio_candidates if path.is_file()), None)
    if script is None:
        raise ProductionBackendError("MPT 需要已批准的本地 video-script")
    if not materials.is_dir() or not any(materials.iterdir()):
        raise ProductionBackendError("MPT 需要非空的 Episode 本地素材目录 work/prepared")
    if audio is None:
        raise ProductionBackendError("MPT 需要已锁定的 custom audio；禁止默认 Edge TTS")
    runtime = root / MPT_RUNTIME_RELATIVE
    if not runtime.is_dir():
        raise ProductionBackendError(
            f"MoneyPrinterTurbo v{MPT_VERSION} runtime 不存在: {runtime}"
        )
    return MPTRequest(script=script, materials=materials, audio=audio, runtime=runtime)


def build_mpt_command(request: MPTRequest) -> list[str]:
    cli = request.runtime / "cli.py"
    if not cli.is_file():
        raise ProductionBackendError(f"MPT v{MPT_VERSION} 缺少 cli.py: {cli}")
    return [
        "uv", "run", "python", str(cli),
        "--video-script", str(request.script),
        "--video-source", "local",
        "--video-materials", str(request.materials),
        "--custom-audio-file", str(request.audio),
        "--video-aspect", "9:16",
        "--stop-at", "video",
    ]


def run_mpt(ep_dir: Path, *, force: bool = False) -> Path:
    request = build_mpt_request(ep_dir)
    command = build_mpt_command(request)
    try:
        result = subprocess.run(
            command, cwd=request.runtime, capture_output=True, text=True,
            timeout=20 * 60, check=False,
        )
    except OSError as exc:
        raise ProductionBackendError(f"MPT v{MPT_VERSION} 无法启动: {exc}") from exc
    output = f"{result.stdout}\n{result.stderr}"
    if result.returncode != 0:
        raise ProductionBackendError(
            f"MPT v{MPT_VERSION} 生产失败（exit {result.returncode}）"
        )
    match = _VIDEO_FILE.search(output)
    if match is None:
        raise ProductionBackendError("MPT 成功返回但未报告 VIDEO_FILE；禁止伪造候选")
    candidate = Path(match.group("path").strip()).resolve()
    if not candidate.is_file() or candidate.stat().st_size == 0:
        raise ProductionBackendError("MPT 报告的 VIDEO_FILE 不存在或为空")
    render_dir = ep_dir / "renders"
    render_dir.mkdir(parents=True, exist_ok=True)
    target = render_dir / "final-with-captions.mp4"
    if target.is_file() and not force:
        raise ProductionBackendError(f"最终视频已存在且不同；请使用 --force: {target}")
    shutil.copy2(candidate, target)
    clean = render_dir / "final-clean.mp4"
    if not clean.is_file() or force:
        shutil.copy2(candidate, clean)
    return target


def produce_publishable_video(ep_dir: Path, production_type: str, *, force: bool = False) -> dict[str, Path]:
    if production_type not in {"STANDARD", "VISUAL_EXPLAINER"}:
        raise ProductionBackendError(f"MPT backend 不支持 production_type={production_type}")
    final = run_mpt(ep_dir, force=force)
    return {"final_with_captions": final, "final_clean": ep_dir / "renders" / "final-clean.mp4"}
