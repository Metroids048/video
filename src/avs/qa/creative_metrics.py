"""Deterministic creative metrics.

Nothing here judges taste — every value is measurable and reproducible.  The
numbers exist so that a later subjective score can be checked against something
falsifiable, and so that "the video got better" can be argued with evidence
rather than asserted.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat

STATIC_DIFF_THRESHOLD = 0.08 * 255  # matches visual_reviewer's perceptual threshold
STATIC_SAMPLE_STEP = 0.5
BLACK_BAND_MEAN = 12.0
BLACK_BAND_FRACTION = 12  # scan 1/12 of each edge
HOOK_WINDOW_SECONDS = 5.0
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920


def probe_duration(video_path: Path) -> float:
    """Container duration in seconds; 0.0 when ffprobe is unavailable."""
    if shutil.which("ffprobe") is None:
        return 0.0
    command = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    if result.returncode != 0:
        return 0.0
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def video_clips(timeline: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        clip
        for track in timeline.get("tracks", [])
        if track.get("kind") == "video"
        for clip in track.get("clips", [])
    ]


def shot_boundaries(timeline: dict[str, Any]) -> list[float]:
    """Cut points, excluding 0.0 which is not a perceived cut."""
    return sorted({
        round(float(clip.get("start", 0.0)), 3)
        for clip in video_clips(timeline)
        if float(clip.get("start", 0.0)) > 0.0
    })


def shot_duration_stats(timeline: dict[str, Any]) -> dict[str, Any]:
    durations = [round(float(clip.get("duration", 0.0)), 3) for clip in video_clips(timeline)]
    durations = [value for value in durations if value > 0]
    if not durations:
        return {
            "shot_count": 0, "shot_duration_distinct_values": 0,
            "shot_duration_min": 0.0, "shot_duration_max": 0.0, "shot_duration_mean": 0.0,
        }
    return {
        "shot_count": len(durations),
        "shot_duration_distinct_values": len(set(durations)),
        "shot_duration_min": min(durations),
        "shot_duration_max": max(durations),
        "shot_duration_mean": round(sum(durations) / len(durations), 3),
    }


def audio_signals(timeline: dict[str, Any]) -> dict[str, Any]:
    roles: set[str] = set()
    providers: list[str] = []
    for track in timeline.get("tracks", []):
        if track.get("kind") != "audio":
            continue
        role = str(track.get("audio_role") or "")
        if role:
            roles.add(role)
        for clip in track.get("clips", []):
            style = clip.get("style") or {}
            if str(style.get("role") or "") == "voice":
                provider = str(style.get("provider") or "unknown")
                if provider not in providers:
                    providers.append(provider)
            clip_role = str(style.get("role") or "")
            if clip_role:
                roles.add(clip_role)
    return {
        "has_bgm": "bgm" in roles or "music" in roles,
        "has_sfx": "sfx" in roles,
        "voice_providers": providers,
    }


def _black_border_ratio(image: Image.Image) -> float:
    width, height = image.size
    band_h = max(1, height // BLACK_BAND_FRACTION)
    band_w = max(1, width // BLACK_BAND_FRACTION)
    bands = (
        (image.crop((0, 0, width, band_h)), band_h / height),
        (image.crop((0, height - band_h, width, height)), band_h / height),
        (image.crop((0, 0, band_w, height)), band_w / width),
        (image.crop((width - band_w, 0, width, height)), band_w / width),
    )
    worst = 0.0
    for band, ratio in bands:
        if max(ImageStat.Stat(band).mean) < BLACK_BAND_MEAN:
            worst = max(worst, ratio)
    return round(worst, 4)


def _difference(first: Path, second: Path) -> float:
    with Image.open(first) as left_raw, Image.open(second) as right_raw:
        left = left_raw.convert("RGB")
        right = right_raw.convert("RGB").resize(left.size)
        stat = ImageStat.Stat(ImageChops.difference(left, right))
    return sum(stat.mean) / len(stat.mean)


def motion_metrics(frames: dict[float, Path]) -> dict[str, Any]:
    """Static-run and change-rate metrics from evenly spaced frames."""
    ordered = sorted(frames.items())
    if len(ordered) < 2:
        return {
            "longest_static_run_seconds": 0.0, "static_frame_ratio": 0.0,
            "hook_static_seconds": 0.0, "visual_change_rate": 0.0,
            "max_black_border_ratio": 0.0,
        }
    diffs: list[tuple[float, float]] = []
    for index in range(1, len(ordered)):
        previous_time, previous_path = ordered[index - 1]
        current_time, current_path = ordered[index]
        diffs.append((current_time, _difference(previous_path, current_path)))
        del previous_time
    static_pairs = [time for time, value in diffs if value < STATIC_DIFF_THRESHOLD]
    longest = 0.0
    run = 0.0
    hook_static = 0.0
    hook_run = 0.0
    for time, value in diffs:
        if value < STATIC_DIFF_THRESHOLD:
            run += STATIC_SAMPLE_STEP
            if time <= HOOK_WINDOW_SECONDS:
                hook_run += STATIC_SAMPLE_STEP
                hook_static = max(hook_static, hook_run)
        else:
            run = 0.0
            hook_run = 0.0
        longest = max(longest, run)
    worst_border = 0.0
    for _, path in ordered:
        with Image.open(path) as raw:
            worst_border = max(worst_border, _black_border_ratio(raw.convert("RGB")))
    return {
        "longest_static_run_seconds": round(longest, 2),
        "static_frame_ratio": round(len(static_pairs) / len(diffs), 4),
        "hook_static_seconds": round(hook_static, 2),
        "visual_change_rate": round(sum(value for _, value in diffs) / len(diffs), 3),
        "max_black_border_ratio": worst_border,
    }


def evidence_scale_factors(
    episode_dir: Path,
    timeline: dict[str, Any],
    *,
    canvas_width: int = CANVAS_WIDTH,
    canvas_height: int = CANVAS_HEIGHT,
) -> list[dict[str, Any]]:
    """How small each visual evidence asset ends up on the vertical canvas.

    A landscape screenshot fitted to canvas width keeps its aspect ratio, so its
    readable band is only ``canvas_width/source_width`` of the original scale.
    That single number explains most "the evidence is unreadable" findings.
    """
    factors: list[dict[str, Any]] = []
    for clip in video_clips(timeline):
        asset_ref = clip.get("asset_ref")
        if not asset_ref:
            continue
        source = episode_dir / str(asset_ref)
        width: int | None = None
        height: int | None = None
        if source.is_file():
            try:
                with Image.open(source) as image:
                    width, height = image.size
            except OSError:
                width, height = None, None
        if width and height:
            scale = canvas_width / width
            band = min(1.0, (height * scale) / canvas_height)
        else:
            scale, band = 0.0, 0.0
        factors.append({
            "asset_ref": str(asset_ref),
            "source_width": width,
            "source_height": height,
            "scale_factor": round(scale, 4),
            "sharp_band_ratio": round(band, 4),
        })
    return factors


def compute_metrics(
    episode_dir: Path,
    video_path: Path,
    timeline: dict[str, Any],
    frames: dict[float, Path],
) -> dict[str, Any]:
    metrics: dict[str, Any] = {"duration_seconds": round(probe_duration(video_path), 3)}
    metrics.update(shot_duration_stats(timeline))
    metrics.update(motion_metrics(frames))
    metrics.update(audio_signals(timeline))
    metrics["evidence_scale_factors"] = evidence_scale_factors(episode_dir, timeline)
    return metrics


def load_timeline(episode_dir: Path) -> dict[str, Any]:
    path = episode_dir / "work" / "timeline.json"
    if not path.is_file():
        return {"tracks": []}
    return json.loads(path.read_text(encoding="utf-8"))
