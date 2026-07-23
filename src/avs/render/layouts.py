"""src/avs/render/layouts.py — 画布布局计算（contain / cover）。

输出 FFmpeg vf 滤镜片段字符串，供 ffmpeg.py 组装。
"""
from __future__ import annotations


def contain_filter(w: int, h: int, canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    """contain：保持纵横比，黑边填充至画布。"""
    return (
        f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=decrease,"
        f"pad={canvas_w}:{canvas_h}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"setsar=1,fps={30}"
    )


def cover_filter(w: int, h: int, canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    """cover：缩放裁切，填满画布无黑边。"""
    return (
        f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=increase,"
        f"crop={canvas_w}:{canvas_h},"
        f"setsar=1,fps={30}"
    )


def image_filter(canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    """图片转视频：contain + fps 强制。"""
    return contain_filter(canvas_w, canvas_h, canvas_w, canvas_h)


def placeholder_card_filter(canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    """占位卡（黑底白字）——通过 drawtext 滤镜在调用方合并。"""
    return f"scale={canvas_w}:{canvas_h},setsar=1"


def choose_layout(transform: dict | None, src_w: int | None, src_h: int | None) -> str:
    """根据 transform.layout 和源尺寸选择适当布局滤镜。"""
    layout = (transform or {}).get("layout", "contain")
    if layout == "cover":
        return cover_filter(src_w or 1080, src_h or 1920)
    # 默认 contain
    return contain_filter(src_w or 1080, src_h or 1920)
