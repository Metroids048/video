"""Provider-backed visual/semantic review gate.

This module deliberately fails closed when semantic vision is unavailable.
The deterministic checks still produce useful timestamped diagnostics for
duplicate/static shots and missing evidence.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import base64
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageChops, ImageStat

from avs.analysis.asset_intelligence import vision_provider_name

SemanticReviewer = Callable[..., list[dict[str, Any]]]
STATIC_FRAME_DIFF_THRESHOLD = 0.08


def _extract_frames(video_path: Path, output_dir: Path, *, force: bool) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(output_dir.glob("frame-*.jpg"))
    if existing and not force:
        return existing
    if force:
        for frame in existing:
            frame.unlink()
    if shutil.which("ffmpeg") is None:
        return []
    command = [
        "ffmpeg", "-y", "-i", str(video_path), "-vf", "fps=1",
        "-q:v", "3", str(output_dir / "frame-%04d.jpg"),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180, check=False)
    if result.returncode != 0:
        return []
    return sorted(output_dir.glob("frame-*.jpg"))


def _has_large_black_border(path: Path) -> bool:
    with Image.open(path).convert("RGB") as image:
        width, height = image.size
        bands = (
            image.crop((0, 0, width, max(1, height // 12))),
            image.crop((0, height - max(1, height // 12), width, height)),
            image.crop((0, 0, max(1, width // 12), height)),
            image.crop((width - max(1, width // 12), 0, width, height)),
        )
        return any(max(ImageStat.Stat(band).mean) < 12 for band in bands)


def _difference_score(first: Path, second: Path) -> float:
    with Image.open(first).convert("RGB") as left, Image.open(second).convert("RGB") as right:
        right = right.resize(left.size)
        stat = ImageStat.Stat(ImageChops.difference(left, right))
        return sum(stat.mean) / len(stat.mean)


def _semantic_prompt(
    script: dict[str, Any], evidence_map: dict[str, Any], shot_plan: dict[str, Any],
    intelligence: dict[str, Any], selection: dict[str, Any],
) -> str:
    context = {
        "script": script,
        "evidence_map": evidence_map,
        "shot_plan": shot_plan,
        "asset_intelligence": intelligence,
        "reference_selection": selection,
    }
    return (
        "你是短视频成片语义质检员。结合按时间顺序提供的抽帧和制作上下文，"
        "逐项检查：旁白与可见画面是否匹配、证据是否真的可见、文字是否可读、"
        "是否出现错误素材或未经证实的产品事实。只返回 JSON 对象："
        '{"failures":[{"timestamp":0,"failure_code":"SEMANTIC_MISMATCH",'
        '"spoken_text":"","visible_content":"","required_fix":""}]}。'
        "没有问题时 failures 为空数组。不得根据上下文臆测画面中没有的内容。\n"
        + json.dumps(context, ensure_ascii=False)[:24000]
    )


def _provider_semantic_review(
    episode_dir: Path,
    *,
    frames: list[Path],
    script: dict[str, Any],
    evidence_map: dict[str, Any],
    shot_plan: dict[str, Any],
    intelligence: dict[str, Any],
    selection: dict[str, Any],
) -> list[dict[str, Any]]:
    from avs.analysis.asset_intelligence import _extract_json, _request_json, _vision_model

    provider = vision_provider_name()
    if provider == "none":
        raise RuntimeError("没有可用 Vision Provider")
    sampled = frames if len(frames) <= 12 else [
        frames[round(index * (len(frames) - 1) / 11)] for index in range(12)
    ]
    prompt = _semantic_prompt(script, evidence_map, shot_plan, intelligence, selection)
    image_items: list[dict[str, Any]] = []
    for frame in sampled:
        encoded = base64.b64encode(frame.read_bytes()).decode("ascii")
        media_type = "image/png" if frame.suffix.lower() == ".png" else "image/jpeg"
        image_items.append({"encoded": encoded, "media_type": media_type})
    model = _vision_model(episode_dir, provider)
    if provider == "anthropic":
        import os
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for item in image_items:
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": item["media_type"], "data": item["encoded"]},
            })
        response = _request_json(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
            {"model": model, "max_tokens": 3072, "messages": [{"role": "user", "content": content}]},
        )
        text = "\n".join(item.get("text", "") for item in response.get("content", []) if item.get("type") == "text")
    else:
        import os
        content = [{"type": "text", "text": prompt}]
        content.extend({
            "type": "image_url",
            "image_url": {"url": f"data:{item['media_type']};base64,{item['encoded']}"},
        } for item in image_items)
        response = _request_json(
            "https://api.openai.com/v1/chat/completions",
            {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            {
                "model": model, "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": content}],
            },
        )
        text = str(response["choices"][0]["message"]["content"])
    payload = _extract_json(text)
    failures: list[dict[str, Any]] = []
    for item in payload.get("failures", []):
        if not isinstance(item, dict):
            continue
        failures.append({
            "timestamp": float(item.get("timestamp", 0.0)),
            "failure_code": str(item.get("failure_code") or "SEMANTIC_MISMATCH"),
            "spoken_text": str(item.get("spoken_text") or ""),
            "visible_content": str(item.get("visible_content") or ""),
            "required_fix": str(item.get("required_fix") or "人工复核并重做该镜头"),
        })
    return failures


def review_video(
    episode_dir: Path,
    *,
    video_path: Path | None = None,
    script: dict[str, Any] | None = None,
    evidence_map: dict[str, Any] | None = None,
    shot_plan: dict[str, Any] | None = None,
    intelligence: dict[str, Any] | None = None,
    selection: dict[str, Any] | None = None,
    semantic_reviewer: SemanticReviewer | None = None,
    force: bool = False,
) -> dict[str, Any]:
    report_path = episode_dir / "work" / "qa" / "visual-review.json"
    if report_path.is_file() and not force:
        return json.loads(report_path.read_text(encoding="utf-8"))
    previous_attempt = 0
    if report_path.is_file():
        try:
            previous_attempt = int(json.loads(report_path.read_text(encoding="utf-8")).get("attempt", 0))
        except (json.JSONDecodeError, ValueError, TypeError):
            previous_attempt = 0
    attempt = previous_attempt + 1
    failures: list[dict[str, Any]] = []
    if video_path is not None:
        source_video = video_path
    else:
        candidates = (
            episode_dir / "renders" / "final-with-captions.mp4",
            episode_dir / "renders" / "preview-with-motion.mp4",
            episode_dir / "renders" / "preview-with-captions.mp4",
        )
        source_video = next((path for path in candidates if path.is_file()), candidates[-1])
    frames: list[Path] = []
    if not source_video.is_file():
        failures.append({
            "timestamp": 0.0,
            "failure_code": "VIDEO_MISSING",
            "spoken_text": "",
            "visible_content": "没有可审核的视频",
            "required_fix": "先生成低清预览",
        })
    else:
        frames = _extract_frames(source_video, episode_dir / "work" / "qa" / "frames", force=force)
        if not frames:
            failures.append({
                "timestamp": 0.0,
                "failure_code": "FRAME_EXTRACTION_FAILED",
                "spoken_text": "",
                "visible_content": str(source_video),
                "required_fix": "检查 FFmpeg 和视频可解码性",
            })
        for index, frame in enumerate(frames):
            if _has_large_black_border(frame):
                failures.append({
                    "timestamp": float(index),
                    "failure_code": "FULL_FRAME_CONTEXT_REVIEW_REQUIRED",
                    "spoken_text": "",
                    "visible_content": frame.name,
                    "required_fix": "对照源录屏确认完整页面上下文；允许保留竖屏未使用空间，不得仅为填满画布裁切",
                })
        duplicate_run = 0
        for index in range(1, len(frames)):
            duplicate_run = (
                duplicate_run + 1
                if _difference_score(frames[index - 1], frames[index]) < STATIC_FRAME_DIFF_THRESHOLD
                else 0
            )
            if duplicate_run >= 3:
                failures.append({
                    "timestamp": float(index - 2),
                    "failure_code": "SCREEN_ACTION_STALLED",
                    "spoken_text": "",
                    "visible_content": frames[index].name,
                    "required_fix": "核对源录屏是否有真实点击、滚动或状态变化；没有真实过程时保持诚实静帧并调整叙事",
                })
                break
    provider = vision_provider_name()
    if provider == "none":
        failures.append({
            "timestamp": 0.0,
            "failure_code": "VISION_PROVIDER_UNAVAILABLE",
            "spoken_text": "",
            "visible_content": "未执行语义视觉审核",
            "required_fix": "配置 ANTHROPIC_API_KEY 或 OPENAI_API_KEY 后重新审核",
        })
    elif frames:
        reviewer = semantic_reviewer or (
            lambda **context: _provider_semantic_review(episode_dir, **context)
        )
        try:
            failures.extend(reviewer(
                frames=frames,
                script=script or {},
                evidence_map=evidence_map or {},
                shot_plan=shot_plan or {},
                intelligence=intelligence or {},
                selection=selection or {},
            ))
        except Exception as exc:
            failures.append({
                "timestamp": 0.0,
                "failure_code": "VISION_REVIEW_FAILED",
                "spoken_text": "",
                "visible_content": f"Provider 语义审核失败: {exc}",
                "required_fix": "检查 Vision Provider 配置后使用 --force 重试",
            })
    if shot_plan:
        elapsed = 0.0
        for shot in shot_plan.get("shots", []):
            duration = float(shot.get("duration_seconds", 0))
            if shot.get("primitive") in {"screenshot_full", "screenshot_stack", "screenshot_compare"} and duration > 3.0:
                failures.append({
                    "timestamp": round(elapsed, 3),
                    "failure_code": "PPT_STATIC_SHOT",
                    "spoken_text": "",
                    "visible_content": shot.get("asset_refs", []),
                    "required_fix": "优先换成真实连续录屏；若只有静态证据则如实呈现，不得用人工镜头运动伪装过程",
                })
            elapsed += duration
    if evidence_map:
        for segment in evidence_map.get("segments", []):
            if segment.get("evidence_required") and not segment.get("asset_refs"):
                failures.append({
                    "timestamp": 0.0,
                    "failure_code": "SEMANTIC_MISMATCH",
                    "spoken_text": segment.get("spoken_text", ""),
                    "visible_content": "无产品证据",
                    "required_fix": "绑定真实产品截图或录屏区域",
                })
    provider_blocked = any(item["failure_code"] in {"VISION_PROVIDER_UNAVAILABLE", "VISION_REVIEW_FAILED"} for item in failures)
    report = {
        "passed": not failures,
        "blocked": provider_blocked or (bool(failures) and attempt >= 2),
        "failures": failures,
        "attempt": attempt,
        "repair_allowed": bool(failures) and not provider_blocked and attempt < 2,
        "sample_interval_seconds": 1.0,
        "frame_count": len(frames),
        "semantic_provider": provider,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
