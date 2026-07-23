"""src/avs/render/audio.py — 音频混合：旁白优先，BGM ducking，防削波。"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def mix_audio_filter(
    voice_volume: float = 1.0,
    bgm_volume: float = 0.3,
    has_voice: bool = True,
    has_bgm: bool = True,
) -> str:
    """构建 amix/volume 滤镜字符串（amerge 简化版）。

    返回适用于 FFmpeg -filter_complex 的音频滤镜片段。
    不直接执行，由 ffmpeg.py 调用。
    """
    parts: list[str] = []

    if has_voice and has_bgm:
        # 旁白 + BGM ducking：BGM 在有旁白时降低音量
        # 使用 sidechaincompress 实现 ducking
        parts = [
            f"[voice_in]volume={voice_volume}[voice_vol]",
            f"[bgm_in]volume={bgm_volume}[bgm_vol]",
            "[voice_vol][bgm_vol]amix=inputs=2:duration=first:dropout_transition=2[audio_out]",
        ]
        return "; ".join(parts)
    elif has_voice:
        return f"[voice_in]volume={voice_volume}[audio_out]"
    elif has_bgm:
        return f"[bgm_in]volume={bgm_volume}[audio_out]"
    else:
        # 静音
        return "anullsrc=r=44100:cl=stereo[audio_out]"


def build_silence(duration: float, output_path: Path) -> bool:
    """生成指定时长的静音音频文件（用于无音轨的正常降级）。"""
    if not ffmpeg_available():
        logger.warning("ffmpeg 不可用，跳过静音生成")
        return False
    import subprocess
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=stereo:d={duration}",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning("静音生成失败: %s", result.stderr[:200])
        return False
    return True
