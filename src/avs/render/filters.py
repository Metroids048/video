"""src/avs/render/filters.py — FFmpeg 滤镜图辅助函数。"""
from __future__ import annotations

from pathlib import Path


def scale_pad_filter(canvas_w: int = 1080, canvas_h: int = 1920, fps: int = 30) -> str:
    """标准 contain 缩放+填充滤镜。"""
    return (
        f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=decrease,"
        f"pad={canvas_w}:{canvas_h}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"setsar=1,fps={fps}"
    )


def scale_crop_filter(canvas_w: int = 1080, canvas_h: int = 1920, fps: int = 30) -> str:
    """cover 缩放+裁切滤镜。"""
    return (
        f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=increase,"
        f"crop={canvas_w}:{canvas_h},"
        f"setsar=1,fps={fps}"
    )


def image_to_video_filter(duration: float, canvas_w: int = 1080, canvas_h: int = 1920, fps: int = 30) -> str:
    """图片转视频 contain 滤镜（不含 loop，由调用方添加 -loop 1）。"""
    return scale_pad_filter(canvas_w, canvas_h, fps)


def placeholder_drawtext_filter(
    text: str,
    canvas_w: int = 1080,
    canvas_h: int = 1920,
    fps: int = 30,
) -> str:
    """黑底白字占位卡滤镜。使用 drawtext 在居中位置绘制文字。"""
    # 转义 FFmpeg drawtext 特殊字符
    safe_text = text.replace("'", "\\'").replace(":", "\\:").replace("\\", "\\\\")
    # 限制长度
    if len(safe_text) > 40:
        safe_text = safe_text[:40] + "..."
    return (
        f"color=c=black:s={canvas_w}x{canvas_h}:r={fps},"
        f"drawtext=text='{safe_text}':fontcolor=white:fontsize=40:"
        f"x=(w-text_w)/2:y=(h-text_h)/2"
    )


def burn_subtitles_filter(srt_path: Path) -> str:
    """字幕烧录滤镜（subtitles filter）。"""
    # Windows 路径需要特殊处理
    path_str = str(srt_path).replace("\\", "/").replace(":", "\\:")
    return f"subtitles='{path_str}':force_style='FontSize=32,PrimaryColour=&HFFFFFF&,Outline=2,Shadow=1,MarginV=80'"
