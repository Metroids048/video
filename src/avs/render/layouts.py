"""src/avs/render/layouts.py — 画布布局计算。

竖屏短视频中的横屏录屏必须优先保证信息可读性。screen_focus 因此使用
单一 9:16 证据视口，而不是“模糊背景 + 缩小横屏”或上下复制画面。
"""
from __future__ import annotations


def contain_filter(w: int, h: int, canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    """contain：保持纵横比，黑边填充至画布。"""
    return (
        f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=decrease,"
        f"pad={canvas_w}:{canvas_h}:(ow-iw)/2:(oh-ih)/2:color=black,"
        "setsar=1,fps=30"
    )


def cover_filter(w: int, h: int, canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    """cover：缩放裁切，填满画布无黑边。"""
    return (
        f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=increase,"
        f"crop={canvas_w}:{canvas_h},"
        "setsar=1,fps=30"
    )


def screen_focus_filter(
    w: int,
    h: int,
    canvas_w: int = 1080,
    canvas_h: int = 1920,
    *,
    focus_x: float = 0.5,
) -> str:
    """横屏录屏的单主画面竖屏适配。

    先把源画面按输出高度放大，再从水平方向裁出一个完整 9:16 视口。
    ``focus_x`` 取 0..1：0 为最左，0.5 为中间，1 为最右。这样 shot plan
    可以显式告诉渲染器当前证据在左侧、中央还是右侧，而不是复制/缩小整屏。
    """
    del w, h  # FFmpeg 用实际输入尺寸计算缩放后的宽度。
    focus = max(0.0, min(1.0, float(focus_x)))
    x_expr = f"max(0,min(iw-{canvas_w},(iw-{canvas_w})*{focus:.4f}))"
    return (
        f"scale=-2:{canvas_h},"
        f"crop={canvas_w}:{canvas_h}:x='{x_expr}':y=0,"
        "setsar=1,fps=30"
    )


def screen_stack_filter(w: int, h: int, canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    """Legacy 内部布局；发布级证据画面不应使用。"""
    scaled_h = int(h * canvas_w / w)
    return (
        f"scale={canvas_w}:{scaled_h},"
        "split[top][bottom];"
        "[top][bottom]vstack,"
        f"crop={canvas_w}:{canvas_h},"
        "setsar=1,fps=30"
    )


def image_filter(canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    """图片转视频：contain + fps 强制。"""
    return contain_filter(canvas_w, canvas_h, canvas_w, canvas_h)


def placeholder_card_filter(canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    """占位卡（黑底白字）——通过 drawtext 滤镜在调用方合并。"""
    return f"scale={canvas_w}:{canvas_h},setsar=1"


def is_landscape(w: int | None, h: int | None) -> bool:
    """判断是否为横屏素材（宽 > 高）。"""
    if w is None or h is None or w <= 0 or h <= 0:
        return False
    return w > h


def choose_layout(
    transform: dict | None,
    src_w: int | None,
    src_h: int | None,
    *,
    default_landscape_strategy: str = "screen_focus",
) -> str:
    """根据 transform.layout 和源尺寸选择布局滤镜。"""
    transform = transform or {}
    layout = transform.get("layout")

    if is_landscape(src_w, src_h):
        if layout == "contain":
            import logging
            logging.warning(
                f"横屏素材 ({src_w}x{src_h}) 不应使用 contain 布局（会产生黑边），"
                f"降级为 {default_landscape_strategy}"
            )
            layout = default_landscape_strategy

        layout = layout or default_landscape_strategy

        if layout == "screen_focus":
            return screen_focus_filter(
                src_w or 1920,
                src_h or 1080,
                focus_x=float(transform.get("focus_x", 0.5)),
            )
        if layout == "screen_stack":
            return screen_stack_filter(src_w or 1920, src_h or 1080)
        if layout == "cover":
            return cover_filter(src_w or 1920, src_h or 1080)
        return screen_focus_filter(
            src_w or 1920,
            src_h or 1080,
            focus_x=float(transform.get("focus_x", 0.5)),
        )

    if layout == "cover":
        return cover_filter(src_w or 1080, src_h or 1920)

    return contain_filter(src_w or 1080, src_h or 1920)
