"""src/avs/render/layouts.py — 画布布局计算（contain / cover / screen_focus / screen_stack）。

输出 FFmpeg vf 滤镜片段字符串，供 ffmpeg.py 组装。

布局策略：
- contain: 保持纵横比，黑边填充（仅用于竖屏或方形素材）
- cover: 缩放裁切，填满画布无黑边
- screen_focus: 横屏录屏，上下添加模糊背景，中间保持清晰
- screen_stack: 横屏录屏，垂直堆叠两次（上下镜像），填满竖屏
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


def screen_focus_filter(w: int, h: int, canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    """screen_focus：横屏录屏，上下模糊背景+中间清晰屏幕。

    适用于横屏录屏内容，保持屏幕清晰可读，背景模糊填充避免黑边。

    实现：
    1. 将输入分为两个流：[main] 和 [bg]
    2. [bg] 缩放到画布高度+裁切+模糊
    3. [main] 缩放保持纵横比
    4. overlay [main] 到 [bg] 中央
    """
    # 计算主屏幕缩放尺寸（保持宽高比，高度为画布的60-70%）
    target_h = int(canvas_h * 0.65)
    target_w = int(w * target_h / h)

    # 如果缩放后宽度超过画布，则按宽度缩放
    if target_w > canvas_w:
        target_w = canvas_w
        target_h = int(h * target_w / w)

    return (
        # 分流
        f"split[main][bg];"
        # 背景：放大裁切+强模糊
        f"[bg]scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=increase,"
        f"crop={canvas_w}:{canvas_h},boxblur=20:2[bg_blur];"
        # 主屏：缩放保持清晰
        f"[main]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease[main_scaled];"
        # 叠加到中央
        f"[bg_blur][main_scaled]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={30}"
    )


def screen_stack_filter(w: int, h: int, canvas_w: int = 1080, canvas_h: int = 1920) -> str:
    """screen_stack：横屏录屏，垂直堆叠填满竖屏。

    适用于横屏录屏内容，通过上下堆叠（可镜像）填满竖屏画布。

    实现：
    1. 将输入缩放到画布宽度
    2. 复制并垂直堆叠两次
    3. 裁切到画布高度
    """
    # 缩放到画布宽度
    scaled_h = int(h * canvas_w / w)

    return (
        f"scale={canvas_w}:{scaled_h},"
        f"split[top][bottom];"
        f"[top][bottom]vstack,"
        f"crop={canvas_w}:{canvas_h},"
        f"setsar=1,fps={30}"
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
    """根据 transform.layout 和源尺寸选择适当布局滤镜。

    Args:
        transform: 包含 layout 字段的 dict
        src_w: 源视频宽度
        src_h: 源视频高度
        default_landscape_strategy: 横屏素材的默认策略

    Returns:
        FFmpeg 滤镜字符串

    规则：
        - 横屏素材（w > h）：
          - 如果 layout 显式为 "contain"，警告并降级到 screen_focus
          - 否则使用 layout 或 default_landscape_strategy
        - 竖屏/方形素材：
          - 使用 layout 或默认 contain
    """
    layout = (transform or {}).get("layout", None)

    # 检测横屏
    if is_landscape(src_w, src_h):
        # 横屏素材拒绝 contain（会产生黑边）
        if layout == "contain":
            import logging
            logging.warning(
                f"横屏素材 ({src_w}x{src_h}) 不应使用 contain 布局（会产生黑边），"
                f"降级为 {default_landscape_strategy}"
            )
            layout = default_landscape_strategy

        # 使用指定布局或默认横屏策略
        layout = layout or default_landscape_strategy

        if layout == "screen_focus":
            return screen_focus_filter(src_w or 1920, src_h or 1080)
        elif layout == "screen_stack":
            return screen_stack_filter(src_w or 1920, src_h or 1080)
        elif layout == "cover":
            return cover_filter(src_w or 1920, src_h or 1080)
        else:
            # 未知布局，降级到 screen_focus
            return screen_focus_filter(src_w or 1920, src_h or 1080)

    # 竖屏或方形素材
    if layout == "cover":
        return cover_filter(src_w or 1080, src_h or 1920)

    # 默认 contain
    return contain_filter(src_w or 1080, src_h or 1920)
