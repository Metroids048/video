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

from avs.ingest.errors import NormalizeError, PathTraversalError

# 目标画布（竖屏）
_CANVAS_W = 540
_CANVAS_H = 960
_VIDEO_CRF = 28
_VIDEO_PRESET = "fast"
_AUDIO_BITRATE = "128k"


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _is_landscape(width: int | None, height: int | None) -> bool:
    if width and height:
        return width > height
    return False


def _build_video_filter(
    width: int | None,
    height: int | None,
    *,
    canvas_w: int = _CANVAS_W,
    canvas_h: int = _CANVAS_H,
) -> str:
    """返回 contain（pad）滤镜字符串；横屏视频明确缩放+填充，禁止静默拉伸。"""
    if _is_landscape(width, height):
        # contain: 等比缩放后在 1080×1920 画布上居中，其余区域填黑
        return (
            f"scale={canvas_w}:{canvas_h}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={canvas_w}:{canvas_h}:(ow-iw)/2:(oh-ih)/2:black"
        )
    return (
        f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=decrease,"
        f"pad={canvas_w}:{canvas_h}:(ow-iw)/2:(oh-ih)/2:black"
    )


def normalize_video(
    src: Path,
    dst: Path,
    probe: dict[str, Any],
    *,
    canvas_w: int = _CANVAS_W,
    canvas_h: int = _CANVAS_H,
    crf: int = _VIDEO_CRF,
) -> None:
    """转码视频为 Proxy；ffmpeg 不可用时直接复制。"""
    dst.parent.mkdir(parents=True, exist_ok=True)

    if not _ffmpeg_available():
        shutil.copy2(src, dst)
        return

    vf = _build_video_filter(
        probe.get("width"), probe.get("height"),
        canvas_w=canvas_w, canvas_h=canvas_h,
    )
    has_audio = probe.get("has_audio")  # None or bool

    cmd = ["ffmpeg", "-y", "-i", str(src), "-vf", vf,
           "-c:v", "libx264", "-crf", str(crf),
           "-preset", _VIDEO_PRESET, "-pix_fmt", "yuv420p"]

    if has_audio is False:
        cmd += ["-an"]
    else:
        cmd += ["-c:a", "aac", "-b:a", _AUDIO_BITRATE]

    cmd.append(str(dst))

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
    if result.returncode != 0:
        dst.unlink(missing_ok=True)
        raise NormalizeError(f"FFmpeg proxy 失败: {result.stderr[-500:]}")


def normalize_asset(
    src: Path,
    dst: Path,
    kind: str,
    probe: dict[str, Any],
    *,
    config: dict[str, Any] | None = None,
) -> None:
    """根据素材类型执行规范化，输出到 dst。"""
    dst.parent.mkdir(parents=True, exist_ok=True)

    if kind == "video":
        settings = config or {}
        normalize_video(
            src, dst, probe,
            canvas_w=int(settings.get("canvas_w", _CANVAS_W)),
            canvas_h=int(settings.get("canvas_h", _CANVAS_H)),
            crf=int(settings.get("video_crf", _VIDEO_CRF)),
        )
    else:
        # 图片、音频、文本、链接、未知：直接复制
        shutil.copy2(src, dst)


def prepared_path(episode_dir: Path, rel_source: str) -> Path:
    """计算 work/prepared/ 中的副本路径（保留相对子目录结构）。

    input/images/photo.jpg → work/prepared/images/photo.jpg
    input/reference/clip.mp4 → work/prepared/reference/clip.mp4
    """
    source = Path(rel_source)
    if source.is_absolute() or ".." in source.parts:
        raise PathTraversalError(f"非法输入相对路径: {rel_source}")
    # 去掉 "input/" 前缀
    parts = source.parts
    if parts and parts[0] == "input":
        sub = Path(*parts[1:])
    else:
        sub = Path(rel_source)
    prepared_root = (episode_dir / "work" / "prepared").resolve()
    target = (prepared_root / sub).resolve()
    try:
        target.relative_to(prepared_root)
    except ValueError as exc:
        raise PathTraversalError(f"工作副本路径逃逸: {rel_source}") from exc
    return target
