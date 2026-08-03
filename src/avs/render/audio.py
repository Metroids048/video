"""src/avs/render/audio.py — 音频混合：旁白优先，BGM ducking，防削波。"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

AUDIO_ROLES = frozenset({"narration", "original_voice", "bgm", "effect", "ambient"})


def audio_assets_by_role(manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Group usable audio assets by explicit Manifest role.

    The active path intentionally ignores filename prefixes.  Assets without a
    role remain visible to the caller so the input gate can request a decision.
    """
    grouped: dict[str, list[dict[str, Any]]] = {role: [] for role in AUDIO_ROLES}
    for asset in manifest.get("assets", []):
        if asset.get("source_type", asset.get("kind")) != "audio" or asset.get("status") != "ok":
            continue
        role = asset.get("audio_role")
        if role in grouped:
            grouped[role].append(asset)
    return grouped


def validate_audio_roles(manifest: dict[str, Any]) -> list[str]:
    """Return IDs of audio assets that have no explicit role."""
    return [
        str(asset.get("asset_id"))
        for asset in manifest.get("assets", [])
        if asset.get("source_type", asset.get("kind")) == "audio"
        and asset.get("status") == "ok"
        and asset.get("audio_role") not in AUDIO_ROLES
    ]


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def mix_audio_filter(
    voice_volume: float = 1.0,
    bgm_volume: float = 0.3,
    has_voice: bool = True,
    has_bgm: bool = True,
) -> str:
    """构建旁白优先的混音滤镜字符串。

    返回适用于 FFmpeg -filter_complex 的音频滤镜片段。
    不直接执行，由 ffmpeg.py 调用。
    """
    parts: list[str] = []

    if has_voice and has_bgm:
        parts = [
            f"[voice_in]volume={voice_volume},asplit=2[voice_vol][voice_sidechain]",
            f"[bgm_in]volume={bgm_volume}[bgm_vol]",
            "[bgm_vol][voice_sidechain]sidechaincompress=threshold=0.04:ratio=10:attack=20:release=450[bgm_ducked]",
            "[voice_vol][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=2,alimiter=limit=0.95[audio_out]",
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
