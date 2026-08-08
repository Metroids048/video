"""Frame sampling and contact-sheet building for creative review.

Uniform ``fps=1`` sampling is not adequate for judging a short video: the hook
decides retention and shot boundaries decide perceived pacing, so both need
denser coverage than the middle of the clip.  Contact sheets are built wide on
purpose — narrow sheets are silently dropped by some agent transports, so the
review package would look present while carrying no pixels.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

HOOK_WINDOW_SECONDS = 5.0
HOOK_STEP_SECONDS = 0.5
BOUNDARY_LEAD_SECONDS = 0.25
BOUNDARY_TRAIL_SECONDS = 0.35
INTERVAL_SECONDS = 3.0
TAIL_OFFSET_SECONDS = 0.4
MIN_SHEET_WIDTH = 2560
MAX_TILES_PER_SHEET = 8


def build_sample_plan(
    duration: float,
    shot_boundaries: list[float] | None = None,
) -> list[dict[str, Any]]:
    """Return ordered ``{timestamp, reason}`` samples covering hook and cuts."""
    if duration <= 0:
        return []
    plan: dict[float, str] = {}

    def put(time: float, reason: str) -> None:
        stamp = round(max(0.0, min(time, max(0.0, duration - 0.05))), 2)
        # First reason wins so hook/boundary intent is not overwritten by interval.
        plan.setdefault(stamp, reason)

    step = HOOK_STEP_SECONDS
    hook_end = min(HOOK_WINDOW_SECONDS, duration)
    current = 0.0
    while current < hook_end:
        put(current, "hook_dense")
        current += step

    for boundary in sorted(shot_boundaries or []):
        if boundary <= 0 or boundary >= duration:
            continue
        put(boundary - BOUNDARY_LEAD_SECONDS, "shot_before")
        put(boundary, "shot_at")
        put(boundary + BOUNDARY_TRAIL_SECONDS, "shot_after")

    current = hook_end
    while current < duration:
        put(current, "interval")
        current += INTERVAL_SECONDS

    put(duration - TAIL_OFFSET_SECONDS, "tail")
    return [{"timestamp": stamp, "reason": plan[stamp]} for stamp in sorted(plan)]


def extract_frames(
    video_path: Path,
    timestamps: list[float],
    output_dir: Path,
    *,
    force: bool = False,
) -> dict[float, Path]:
    """Extract one frame per timestamp. Missing ffmpeg yields an empty mapping."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if shutil.which("ffmpeg") is None:
        return {}
    frames: dict[float, Path] = {}
    for stamp in timestamps:
        target = output_dir / f"t{stamp:07.2f}.png"
        if target.is_file() and not force:
            frames[stamp] = target
            continue
        command = [
            "ffmpeg", "-y", "-v", "error", "-ss", f"{stamp:.2f}",
            "-i", str(video_path), "-frames:v", "1", "-pix_fmt", "rgb24", str(target),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
        if result.returncode == 0 and target.is_file():
            frames[stamp] = target
    return frames


def extract_uniform_frames(
    video_path: Path,
    output_dir: Path,
    *,
    step_seconds: float,
    force: bool = False,
) -> dict[float, Path]:
    """Extract evenly spaced frames in one ffmpeg pass.

    Static-run duration is derived by counting consecutive low-difference pairs
    and multiplying by the step, so the spacing has to be uniform.  The review
    sample plan is deliberately non-uniform and cannot be reused here.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(output_dir.glob("u-*.png"))
    if existing and not force:
        return {
            round(index * step_seconds, 2): path
            for index, path in enumerate(existing)
        }
    if shutil.which("ffmpeg") is None:
        return {}
    for stale in existing:
        stale.unlink()
    command = [
        "ffmpeg", "-y", "-v", "error", "-i", str(video_path),
        "-vf", f"fps=1/{step_seconds}", "-pix_fmt", "rgb24",
        str(output_dir / "u-%04d.png"),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
    if result.returncode != 0:
        return {}
    return {
        round(index * step_seconds, 2): path
        for index, path in enumerate(sorted(output_dir.glob("u-*.png")))
    }


def _label_font(size: int) -> Any:
    for name in ("arial.ttf", "DejaVuSans.ttf", "seguisb.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build_contact_sheets(
    frames: dict[float, Path],
    output_dir: Path,
    *,
    label: str = "review",
    min_width: int = MIN_SHEET_WIDTH,
    max_tiles: int = MAX_TILES_PER_SHEET,
) -> list[dict[str, Any]]:
    """Tile frames into sheets at least ``min_width`` px wide, with time labels."""
    if not frames:
        return []
    output_dir.mkdir(parents=True, exist_ok=True)
    ordered = sorted(frames.items())
    sheets: list[dict[str, Any]] = []
    header = 48
    font = _label_font(28)
    for index in range(0, len(ordered), max_tiles):
        chunk = ordered[index:index + max_tiles]
        tile_width = max(1, -(-min_width // len(chunk)))  # ceil so width >= min_width
        tiles: list[tuple[float, Image.Image]] = []
        for stamp, path in chunk:
            with Image.open(path) as raw:
                image = raw.convert("RGB")
            height = max(1, round(tile_width * image.height / image.width))
            tiles.append((stamp, image.resize((tile_width, height), Image.LANCZOS)))
        sheet_width = tile_width * len(tiles)
        sheet_height = max(tile.height for _, tile in tiles) + header
        sheet = Image.new("RGB", (sheet_width, sheet_height), (18, 18, 18))
        draw = ImageDraw.Draw(sheet)
        offset = 0
        for stamp, tile in tiles:
            sheet.paste(tile, (offset, header))
            draw.text((offset + 10, 10), f"t={stamp:.2f}s", fill=(255, 214, 0), font=font)
            offset += tile_width
        sheet_path = output_dir / f"sheet-{label}-{index // max_tiles + 1:02d}.png"
        sheet.save(sheet_path)
        sheets.append({
            "path": sheet_path.as_posix(),
            "label": f"{label} #{index // max_tiles + 1}",
            "width": sheet_width,
            "timestamps": [stamp for stamp, _ in tiles],
        })
    return sheets
