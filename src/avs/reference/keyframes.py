"""src/avs/reference/keyframes.py — 每个镜头提取一帧关键帧。

FFmpeg 不可用时返回空列表（不崩溃）。
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from avs.reference.shots import Shot

log = logging.getLogger(__name__)


def extract_keyframes(
    video_path: Path,
    shots: list[Shot],
    output_dir: Path,
    *,
    timeout_per_frame: int = 20,
    force: bool = False,
) -> dict[str, Path]:
    """为每个镜头在 start+0.5s 位置提取 JPEG 关键帧。

    返回 {shot_id: image_path}，失败的镜头不包含在字典中。
    FFmpeg 不可用时返回空字典。
    """
    if not shutil.which("ffmpeg"):
        log.warning("ffmpeg 不可用，跳过关键帧提取")
        return {}

    output_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Path] = {}

    for shot in shots:
        seek_time = shot.start + min(0.5, (shot.end - shot.start) * 0.5)
        out_path = output_dir / f"{shot.shot_id}.jpg"

        if out_path.exists() and not force:
            result[shot.shot_id] = out_path
            continue

        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{seek_time:.3f}",
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "3",        # JPEG 质量（1=最好，31=最差）
            str(out_path),
        ]
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=timeout_per_frame, check=False,
            )
            if r.returncode == 0 and out_path.exists():
                result[shot.shot_id] = out_path
            else:
                log.warning("关键帧提取失败 (%s, seek=%.3fs): %s",
                            shot.shot_id, seek_time, r.stderr[:100])
        except subprocess.TimeoutExpired:
            log.warning("关键帧提取超时: %s", shot.shot_id)
        except Exception as exc:
            log.warning("关键帧提取异常 (%s): %s", shot.shot_id, exc)

    log.info("关键帧: %d/%d 成功", len(result), len(shots))
    return result
