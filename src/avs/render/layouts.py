"""src/avs/render/layouts.py — 画布布局计算。

发布级桌面/软件录屏默认必须完整保留源画面。横屏转 9:16 时，优先等比例
缩放并留出竖向空间；任何会裁掉源画面的 screen_focus/cover/screen_stack
都属于 destructive crop，只有显式 allow_destructive_crop=true 才允许。
"""
from __future__ import annotations

import logging


_DESTRUCTIVE_LANDSCAPE_LAYOUTS = {"screen_focus", "roi_crop", "cover", "screen_stack"}
_FULL_FRAME_LAYOUTS = {None, "contain", "fit_full_frame"}


def contain_filter(w: int, h: int, canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    """完整保留源画面：等比例缩放后居中填充，不裁切任何边缘。"""
    del w, h
    return (
        f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=decrease,"
        f"pad={canvas_w}:{canvas_h}:(ow-iw)/2:(oh-ih)/2:color=black,"
        "setsar=1,fps=30"
    )


def fit_full_frame_filter(w: int, h: int, canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    """语义别名：发布级横屏录屏默认使用完整画面适配。"""
    return contain_filter(w, h, canvas_w, canvas_h)


def cover_filter(w: int, h: int, canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    """cover：填满画布，但会裁切源画面。仅限显式授权场景。"""
    del w, h
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
    """显式 ROI 裁切。

    这是 destructive crop：会丢失横屏左右上下文。只能由调用方在已经建立完整
    页面上下文后显式授权使用，不能作为横屏录屏默认布局。
    """
    del w, h
    focus = max(0.0, min(1.0, float(focus_x)))
    x_expr = f"max(0,min(iw-{canvas_w},(iw-{canvas_w})*{focus:.4f}))"
    return (
        f"scale=-2:{canvas_h},"
        f"crop={canvas_w}:{canvas_h}:x='{x_expr}':y=0,"
        "setsar=1,fps=30"
    )


def screen_stack_filter(w: int, h: int, canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    """Legacy 内部布局；会重组/裁切画面，发布级默认禁用。"""
    scaled_h = int(h * canvas_w / w)
    return (
        f"scale={canvas_w}:{scaled_h},"
        "split[top][bottom];"
        "[top][bottom]vstack,"
        f"crop={canvas_w}:{canvas_h},"
        "setsar=1,fps=30"
    )


def image_filter(canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    return contain_filter(canvas_w, canvas_h, canvas_w, canvas_h)


def placeholder_card_filter(canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    return f"scale={canvas_w}:{canvas_h},setsar=1"


def is_landscape(w: int | None, h: int | None) -> bool:
    if w is None or h is None or w <= 0 or h <= 0:
        return False
    return w > h


def _destructive_crop_authorized(transform: dict) -> bool:
    return transform.get("allow_destructive_crop") is True


def choose_layout(
    transform: dict | None,
    src_w: int | None,
    src_h: int | None,
    *,
    default_landscape_strategy: str = "fit_full_frame",
) -> str:
    """根据 transform.layout 和源尺寸选择布局。

    安全规则：横屏素材默认完整保留。即使旧配置仍传入 screen_focus/cover/
    screen_stack，若没有 allow_destructive_crop=true，也必须回退到完整画面。
    ``default_landscape_strategy`` 不能绕过这条安全规则。
    """
    transform = transform or {}
    layout = transform.get("layout")

    if is_landscape(src_w, src_h):
        requested = layout if layout is not None else default_landscape_strategy

        if requested in _FULL_FRAME_LAYOUTS or requested not in _DESTRUCTIVE_LANDSCAPE_LAYOUTS:
            return fit_full_frame_filter(src_w or 1920, src_h or 1080)

        if not _destructive_crop_authorized(transform):
            logging.warning(
                "landscape destructive crop '%s' was requested without explicit authorization; "
                "falling back to fit_full_frame",
                requested,
            )
            return fit_full_frame_filter(src_w or 1920, src_h or 1080)

        if requested in {"screen_focus", "roi_crop"}:
            return screen_focus_filter(
                src_w or 1920,
                src_h or 1080,
                focus_x=float(transform.get("focus_x", 0.5)),
            )
        if requested == "screen_stack":
            return screen_stack_filter(src_w or 1920, src_h or 1080)
        if requested == "cover":
            return cover_filter(src_w or 1920, src_h or 1080)

        return fit_full_frame_filter(src_w or 1920, src_h or 1080)

    if layout == "cover":
        return cover_filter(src_w or 1080, src_h or 1920)

    return contain_filter(src_w or 1080, src_h or 1920)
