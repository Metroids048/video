"""src/avs/ingest/normalize.py — 创建工作副本与 Proxy。

规则：
- 原文件只读，只写 work/prepared/ 副本
- 视频：ffmpeg 可用时降码率 Proxy；横屏强制 contain（pad 黑边）
- 无音频视频：跳过音频流，不报错
- ffmpeg 不可用：直接 shutil.copy2
- 所有路径相对于 episode_dir
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

# 目标画布（竖屏）
_CANVAS_W = 1080
_CANVAS_H = 1920
_VIDEO_CRF = 28
_VIDEO_PRESET = "fast"
_AUDIO_BITRATE = "128k"


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _is_landscape(width: int | None, height: int | None) -> bool:
    if width and height:
        return width > height
    return False


def _build_video_filter(width: int | None, height: int | None) -> str:
    """返回 contain（pad）滤镜字符串；横屏视频明确缩放+填充，禁止静默拉伸。"""
    if _is_landscape(width, height):
        # contain: 等比缩放后在 1080×1920 画布上居中，其余区域填黑
        return (
            f"scale={_CANVAS_W}:{_CANVAS_H}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={_CANVAS_W}:{_CANVAS_H}:(ow-iw)/2:(oh-ih)/2:black"
        )
    # 竖屏或未知：等比缩放到目标宽度
    return f"scale={_CANVAS_W}:-2"


def normalize_video(src: Path, dst: Path, probe: dict[str, Any]) -> None:
    """转码视频为 Proxy；ffmpeg 不可用时直接复制。"""
    dst.parent.mkdir(parents=True, exist_ok=True)

    if not _ffmpeg_available():
        shutil.copy2(src, dst)
        return

    vf = _build_video_filter(probe.get("width"), probe.get("height"))
    has_audio = probe.get("has_audio")  # None or bool

    cmd = ["ffmpeg", "-y", "-i", str(src), "-vf", vf,
           "-c:v", "libx264", "-crf", str(_VIDEO_CRF),
           "-preset", _VIDEO_PRESET, "-pix_fmt", "yuv420p"]

    if has_audio is False:
        cmd += ["-an"]
    else:
        cmd += ["-c:a", "aac", "-b:a", _AUDIO_BITRATE]

    cmd.append(str(dst))

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
    if result.returncode != 0:
        # 降级：直接复制，不失败整个 ingest
        shutil.copy2(src, dst)


def normalize_asset(src: Path, dst: Path, kind: str, probe: dict[str, Any]) -> None:
    """根据素材类型执行规范化，输出到 dst。"""
    dst.parent.mkdir(parents=True, exist_ok=True)

    if kind == "video":
        normalize_video(src, dst, probe)
    else:
        # 图片、音频、文本、链接、未知：直接复制
        shutil.copy2(src, dst)


def prepared_path(episode_dir: Path, rel_source: str) -> Path:
    """计算 work/prepared/ 中的副本路径（保留相对子目录结构）。

    input/images/photo.jpg → work/prepared/images/photo.jpg
    input/reference/clip.mp4 → work/prepared/reference/clip.mp4
    """
    # 去掉 "input/" 前缀
    parts = Path(rel_source).parts
    if parts and parts[0] == "input":
        sub = Path(*parts[1:])
    else:
        sub = Path(rel_source)
    return episode_dir / "work" / "prepared" / sub
