"""src/avs/reference/contact_sheet.py — 关键帧联系表（缩略图网格）。

优先 Pillow；其次 FFmpeg tile filter；均不可用时跳过（不崩溃）。
"""
from __future__ import annotations

import logging
import math
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

_THUMB_W = 320
_THUMB_H = 180
_COLS = 4


def make_contact_sheet(
    keyframe_paths: dict[str, Path],   # {shot_id: image_path}
    output_path: Path,
    *,
    cols: int = _COLS,
    thumb_w: int = _THUMB_W,
    thumb_h: int = _THUMB_H,
) -> Path | None:
    """生成关键帧联系表；失败时返回 None（不抛异常）。"""
    if not keyframe_paths:
        log.info("无关键帧，跳过联系表生成")
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    paths = [p for p in keyframe_paths.values() if p.exists()]
    if not paths:
        return None

    # 尝试 Pillow
    result = _make_with_pillow(paths, output_path, cols=cols, thumb_w=thumb_w, thumb_h=thumb_h)
    if result:
        return result

    # 回退：FFmpeg tile filter
    result = _make_with_ffmpeg(paths, output_path, cols=cols, thumb_w=thumb_w, thumb_h=thumb_h)
    if result:
        return result

    log.warning("联系表生成跳过（Pillow 和 FFmpeg 均不可用）")
    return None


def _make_with_pillow(
    paths: list[Path],
    output_path: Path,
    *,
    cols: int,
    thumb_w: int,
    thumb_h: int,
) -> Path | None:
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        return None

    rows = math.ceil(len(paths) / cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (30, 30, 30))

    for i, p in enumerate(paths):
        try:
            img = Image.open(p).convert("RGB")
            img.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            # 居中粘贴（contain）
            x_off = (thumb_w - img.width) // 2
            y_off = (thumb_h - img.height) // 2
            col, row = i % cols, i // cols
            sheet.paste(img, (col * thumb_w + x_off, row * thumb_h + y_off))
        except Exception as exc:
            log.debug("联系表 Pillow 跳过帧 %s: %s", p.name, exc)

    try:
        sheet.save(str(output_path))
        log.info("联系表生成（Pillow）: %s", output_path)
        return output_path
    except Exception as exc:
        log.warning("联系表 Pillow 保存失败: %s", exc)
        return None


def _make_with_ffmpeg(
    paths: list[Path],
    output_path: Path,
    *,
    cols: int,
    thumb_w: int,
    thumb_h: int,
) -> Path | None:
    if not shutil.which("ffmpeg"):
        return None

    # 用 concat demuxer + tile filter
    import os
    import tempfile
    n = len(paths)
    rows = math.ceil(n / cols)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        list_file = f.name
        for p in paths:
            f.write(f"file '{str(p).replace(chr(92), chr(47))}'\n")
            f.write("duration 1\n")

    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", list_file,
            "-vf", f"scale={thumb_w}:{thumb_h}:force_original_aspect_ratio=decrease,"
                   f"pad={thumb_w}:{thumb_h}:(ow-iw)/2:(oh-ih)/2:black,"
                   f"tile={cols}x{rows}",
            "-frames:v", "1",
            str(output_path),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
        if r.returncode == 0 and output_path.exists():
            log.info("联系表生成（FFmpeg）: %s", output_path)
            return output_path
        log.warning("联系表 FFmpeg 失败: %s", r.stderr[:100])
    except Exception as exc:
        log.warning("联系表 FFmpeg 异常: %s", exc)
    finally:
        try:
            os.unlink(list_file)
        except OSError:
            pass
    return None
