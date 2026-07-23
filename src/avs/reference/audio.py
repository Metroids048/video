"""src/avs/reference/audio.py — 从视频中提取音频轨。

FFmpeg 不可用时：返回 None（不崩溃流程）。
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


def extract_audio(
    video_path: Path,
    output_path: Path,
    *,
    sample_rate: int = 16000,
    channels: int = 1,
    timeout: int = 120,
) -> Path | None:
    """提取视频音频为 WAV，返回输出路径；失败或无 FFmpeg 时返回 None。

    sample_rate=16000 适合 Whisper 转写。
    output_path 由调用者指定（幂等：若已存在且非强制则跳过）。
    """
    if not shutil.which("ffmpeg"):
        log.warning("ffmpeg 不可用，跳过音频提取: %s", video_path.name)
        return None

    if output_path.exists():
        log.info("音频已存在，跳过提取: %s", output_path)
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",                     # 去掉视频流
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-f", "wav",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode != 0:
        log.warning("音频提取失败 (%s): %s", video_path.name, result.stderr[:200])
        return None

    log.info("音频提取完成: %s", output_path)
    return output_path


def has_audio_track(video_path: Path, *, timeout: int = 15) -> bool | None:
    """用 ffprobe 检测视频是否含音频流；不可用时返回 None。"""
    if not shutil.which("ffprobe"):
        return None
    cmd = [
        "ffprobe", "-v", "quiet",
        "-select_streams", "a",
        "-show_entries", "stream=codec_type",
        "-of", "csv=p=0",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    return result.returncode == 0 and bool(result.stdout.strip())
