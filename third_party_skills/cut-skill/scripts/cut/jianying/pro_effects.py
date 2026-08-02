"""cut.jianying.pro_effects — 专业特效库（基于剪映大神工作流调研）。

实现专业剪辑师常用的高级特效：
- 不透明度转场（opacity transition，关键帧 alpha 0→1）
- 闪白/闪黑转场（flash white/black）
- 动态模糊转场（motion blur via rapid scale）
- 推拉转场（zoom transition）
- 文字蒙版镂空（text mask cutout）
- 抠像合成预设（green screen keyer）
- 节奏卡点（beat sync）
"""
from __future__ import annotations

import copy
from typing import Optional, Dict, Any, Union

from .draft import Draft, _new_id, _us, _hms
from .effects import add_keyframe


def add_opacity_transition(draft, left_segment_id, right_segment_id,
                           duration_us=500_000, overlap_us=250_000):
    """不透明度转场：左右段都加 alpha 关键帧形成淡入淡出。"""
    left_raw = draft.get_segment_raw(left_segment_id)
    right_raw = draft.get_segment_raw(right_segment_id)
    if not left_raw or not right_raw:
        raise KeyError("left/right segment 不存在")

    right_tt = right_raw.get("target_timerange", {})
    right_start = int(right_tt.get("start", 0))
    add_keyframe(draft, right_segment_id, right_start, 0.0, field="alpha")
    add_keyframe(draft, right_segment_id, right_start + duration_us, 1.0, field="alpha")

    left_tt = left_raw.get("target_timerange", {})
    left_end = int(left_tt.get("start", 0)) + int(left_tt.get("duration", 0))
    add_keyframe(draft, left_segment_id, left_end - duration_us, 1.0, field="alpha")
    add_keyframe(draft, left_segment_id, left_end, 0.0, field="alpha")
    return right_segment_id


def add_flash_transition(draft, left_segment_id, right_segment_id,
                         color="white", duration_us=300_000, peak_alpha=1.0):
    """闪白/闪黑转场：在两段之间插入全屏纯色片段，alpha 0→peak→0。"""
    left_raw = draft.get_segment_raw(left_segment_id)
    if not left_raw:
        raise KeyError(f"left segment {left_segment_id} 不存在")

    left_tt = left_raw.get("target_timerange", {})
    flash_start = int(left_tt.get("start", 0)) + int(left_tt.get("duration", 0)) - duration_us // 2

    color_map = {"white": "#FFFFFF", "black": "#000000", "red": "#FF0000", "blue": "#0000FF"}
    color_value = color_map.get(color, color)

    mat_id = _new_id()
    color_mat = {
        "id": mat_id, "type": "color", "color": color_value,
        "width": 1920, "height": 1080, "duration": duration_us,
        "material_name": f"flash_{color}", "is_valid": True,
    }
    draft.add_material("video", color_mat)

    vts = draft.video_tracks
    overlay_track_id = vts[1].id if len(vts) >= 2 else draft.add_track("video")

    seg = {
        "id": _new_id(), "material_id": mat_id,
        "source_timerange": {"start": 0, "duration": duration_us},
        "target_timerange": {"start": flash_start, "duration": duration_us},
        "source_in_speed": 1.0, "speed": 1.0, "volume": 1.0,
        "common_keyframes": [], "enabled": True, "render_index": 1,
        "track_id": overlay_track_id, "visible": True, "is_placeholder": False,
        "clip": {"alpha": 0.0, "flip": {"horizontal": False, "vertical": False},
                 "rotation": 0, "scale": {"x": 1.0, "y": 1.0}, "transform": {"x": 0, "y": 0}},
        "extra_material_refs": [],
    }
    flash_sid = draft.add_segment_raw(overlay_track_id, seg)

    add_keyframe(draft, flash_sid, flash_start, 0.0, field="alpha")
    add_keyframe(draft, flash_sid, flash_start + duration_us // 2, peak_alpha, field="alpha")
    add_keyframe(draft, flash_sid, flash_start + duration_us, 0.0, field="alpha")

    return {"flash_segment_id": flash_sid, "color": color_value, "duration_us": duration_us}


def add_flash_white(draft, left_id, right_id, **kw):
    return add_flash_transition(draft, left_id, right_id, color="white", **kw)


def add_flash_black(draft, left_id, right_id, **kw):
    return add_flash_transition(draft, left_id, right_id, color="black", **kw)


def add_zoom_transition(draft, left_segment_id, right_segment_id,
                        direction="in", zoom_factor=2.0, duration_us=500_000):
    """推拉转场：左段 scale 1→zoom，右段 scale zoom→1。"""
    left_raw = draft.get_segment_raw(left_segment_id)
    right_raw = draft.get_segment_raw(right_segment_id)
    if not left_raw or not right_raw:
        raise KeyError("left/right segment 不存在")

    left_tt = left_raw.get("target_timerange", {})
    left_end = int(left_tt.get("start", 0)) + int(left_tt.get("duration", 0))
    right_tt = right_raw.get("target_timerange", {})
    right_start = int(right_tt.get("start", 0))

    if direction == "in":
        add_keyframe(draft, left_segment_id, left_end - duration_us, 1.0, field="scale")
        add_keyframe(draft, left_segment_id, left_end, zoom_factor, field="scale")
        add_keyframe(draft, right_segment_id, right_start, zoom_factor, field="scale")
        add_keyframe(draft, right_segment_id, right_start + duration_us, 1.0, field="scale")
    else:
        add_keyframe(draft, left_segment_id, left_end - duration_us, zoom_factor, field="scale")
        add_keyframe(draft, left_segment_id, left_end, 1.0, field="scale")
        add_keyframe(draft, right_segment_id, right_start, 1.0, field="scale")
        add_keyframe(draft, right_segment_id, right_start + duration_us, zoom_factor, field="scale")

    add_keyframe(draft, left_segment_id, left_end - duration_us // 2, 1.0, field="alpha")
    add_keyframe(draft, left_segment_id, left_end, 0.0, field="alpha")
    add_keyframe(draft, right_segment_id, right_start, 0.0, field="alpha")
    add_keyframe(draft, right_segment_id, right_start + duration_us // 2, 1.0, field="alpha")

    return {"direction": direction, "zoom_factor": zoom_factor, "duration_us": duration_us}


def add_motion_blur_transition(draft, left_segment_id, right_segment_id,
                               duration_us=400_000, intensity=1.5):
    """动态模糊转场：用快速 scale + 位移 + alpha 模拟运动模糊。"""
    left_raw = draft.get_segment_raw(left_segment_id)
    right_raw = draft.get_segment_raw(right_segment_id)
    if not left_raw or not right_raw:
        raise KeyError("left/right segment 不存在")

    left_tt = left_raw.get("target_timerange", {})
    left_end = int(left_tt.get("start", 0)) + int(left_tt.get("duration", 0))
    right_tt = right_raw.get("target_timerange", {})
    right_start = int(right_tt.get("start", 0))

    add_keyframe(draft, left_segment_id, left_end - duration_us, 1.0, field="scale")
    add_keyframe(draft, left_segment_id, left_end, intensity, field="scale")
    add_keyframe(draft, left_segment_id, left_end - duration_us, 1.0, field="alpha")
    add_keyframe(draft, left_segment_id, left_end, 0.0, field="alpha")
    add_keyframe(draft, left_segment_id, left_end - duration_us, 0.0, field="position_x")
    add_keyframe(draft, left_segment_id, left_end, 0.3, field="position_x")

    add_keyframe(draft, right_segment_id, right_start, intensity, field="scale")
    add_keyframe(draft, right_segment_id, right_start + duration_us, 1.0, field="scale")
    add_keyframe(draft, right_segment_id, right_start, 0.0, field="alpha")
    add_keyframe(draft, right_segment_id, right_start + duration_us, 1.0, field="alpha")
    add_keyframe(draft, right_segment_id, right_start, -0.3, field="position_x")
    add_keyframe(draft, right_segment_id, right_start + duration_us, 0.0, field="position_x")

    return {"intensity": intensity, "duration_us": duration_us}


def add_text_mask_cutout(draft, text, background_segment_id, start_us,
                         duration_us=3_000_000, font_size=200,
                         position_y=0.0, mask_color="#000000"):
    """文字蒙版镂空：黑底镂空文字露出下层视频。"""
    bg_raw = draft.get_segment_raw(background_segment_id)
    if not bg_raw:
        raise KeyError(f"background segment {background_segment_id} 不存在")

    bg_mat_id = _new_id()
    bg_mat = {
        "id": bg_mat_id, "type": "color", "color": mask_color,
        "width": 1920, "height": 1080, "duration": duration_us,
        "material_name": "mask_bg", "is_valid": True,
    }
    draft.add_material("video", bg_mat)

    text_mat_id = _new_id()
    text_mat = {
        "id": text_mat_id, "type": "title", "text": text, "content": text,
        "base_content": text, "text_size": font_size, "text_color": "#FFFFFF",
        "background_alpha": 0.0, "alignment": 1, "font_size": font_size,
        "transform": {"x": 0.0, "y": position_y}, "scale": {"x": 1.0, "y": 1.0},
        "text_styles": [{"text": text, "style": {"text_size": font_size}}],
        "is_valid": True, "create_segment": True,
    }
    draft.add_material("text", text_mat)

    vts = draft.video_tracks
    overlay_track_id = vts[1].id if len(vts) >= 2 else draft.add_track("video")

    bg_seg = {
        "id": _new_id(), "material_id": bg_mat_id,
        "source_timerange": {"start": 0, "duration": duration_us},
        "target_timerange": {"start": start_us, "duration": duration_us},
        "source_in_speed": 1.0, "speed": 1.0, "volume": 1.0,
        "common_keyframes": [], "enabled": True, "render_index": 2,
        "track_id": overlay_track_id, "visible": True, "is_placeholder": False,
        "clip": {"alpha": 1.0, "scale": {"x": 1.0, "y": 1.0}, "transform": {"x": 0, "y": 0}},
        "mask_info": {
            "mask_id": text_mat_id, "mask_name": "text", "mask_path": "",
            "mask_type": "text", "mask_text": text, "mask_inverted": True,
        },
        "extra_material_refs": [text_mat_id],
    }
    bg_sid = draft.add_segment_raw(overlay_track_id, bg_seg)

    add_keyframe(draft, bg_sid, start_us, 0.0, field="alpha")
    add_keyframe(draft, bg_sid, start_us + 300_000, 1.0, field="alpha")
    add_keyframe(draft, bg_sid, start_us + duration_us - 300_000, 1.0, field="alpha")
    add_keyframe(draft, bg_sid, start_us + duration_us, 0.0, field="alpha")

    return {"mask_segment_id": bg_sid, "text": text, "font_size": font_size}


def apply_beat_sync(draft, track_id, beat_times_us, snap_window_us=200_000):
    """按节拍时间点对齐片段边界。"""
    track = draft.get_track(track_id)
    if not track.segments:
        return {"snapped": 0}

    snapped = 0
    for seg in track.segments:
        raw = draft.get_segment_raw(seg.id)
        if not raw:
            continue
        tt = raw.get("target_timerange", {})
        cur_start = int(tt.get("start", 0))
        nearest = min(beat_times_us, key=lambda b: abs(b - cur_start))
        if abs(nearest - cur_start) <= snap_window_us:
            tt["start"] = nearest
            snapped += 1

    draft.extend_duration()
    return {"snapped": snapped, "total_beats": len(beat_times_us)}


def apply_green_screen_keyer(draft, segment_id, key_color="#00FF00",
                             threshold=0.3, smoothness=0.1):
    """给 segment 应用绿幕抠像预设。"""
    fx_id = _new_id()
    fx_mat = {
        "id": fx_id, "type": "effect", "resource_id": "effect.green_screen",
        "name": "Green Screen Keyer", "category_name": "video_effect",
        "is_affect_video": True, "is_affect_audio": False, "is_valid": True,
        "params": [
            {"key": "key_color", "value": key_color},
            {"key": "threshold", "value": threshold},
            {"key": "smoothness", "value": smoothness},
        ],
    }
    draft.add_material("effect", fx_mat)
    target_seg = draft.get_segment_raw(segment_id)
    if target_seg:
        refs = target_seg.setdefault("extra_material_refs", [])
        refs.append(fx_id)
        draft._modified = True
    return fx_id


PRO_TRANSITION_PRESETS = {
    "smooth": {"type": "opacity", "duration_us": 500_000},
    "flash_white": {"type": "flash_white", "duration_us": 300_000},
    "flash_black": {"type": "flash_black", "duration_us": 300_000},
    "zoom_in": {"type": "zoom", "direction": "in", "zoom_factor": 2.0, "duration_us": 500_000},
    "zoom_out": {"type": "zoom", "direction": "out", "zoom_factor": 2.0, "duration_us": 500_000},
    "motion_blur": {"type": "motion_blur", "intensity": 1.5, "duration_us": 400_000},
    "cinematic": {"type": "flash_black", "duration_us": 500_000, "peak_alpha": 0.7},
    "vlog": {"type": "opacity", "duration_us": 400_000},
}


def apply_pro_transition(draft, left_segment_id, right_segment_id,
                        preset="smooth", **overrides):
    """应用专业转场预设。"""
    if preset not in PRO_TRANSITION_PRESETS:
        raise KeyError(f"未知转场预设: {preset}. 可选: {list(PRO_TRANSITION_PRESETS)}")

    cfg = {**PRO_TRANSITION_PRESETS[preset], **overrides}
    t = cfg["type"]

    if t == "opacity":
        add_opacity_transition(draft, left_segment_id, right_segment_id,
                              duration_us=cfg["duration_us"])
    elif t == "flash_white":
        add_flash_white(draft, left_segment_id, right_segment_id,
                       duration_us=cfg["duration_us"], peak_alpha=cfg.get("peak_alpha", 1.0))
    elif t == "flash_black":
        add_flash_black(draft, left_segment_id, right_segment_id,
                       duration_us=cfg["duration_us"], peak_alpha=cfg.get("peak_alpha", 1.0))
    elif t == "zoom":
        add_zoom_transition(draft, left_segment_id, right_segment_id,
                           direction=cfg["direction"], zoom_factor=cfg["zoom_factor"],
                           duration_us=cfg["duration_us"])
    elif t == "motion_blur":
        add_motion_blur_transition(draft, left_segment_id, right_segment_id,
                                   duration_us=cfg["duration_us"], intensity=cfg["intensity"])

    return {"preset": preset, "config": cfg}
