"""cut.jianying.effects — 转场与特效。

剪映特效结构：
- 转场：每个 video track 有 transitions 数组，每个 transition 关联两个相邻 segment
- 特效：materials.effects 数组，segment 通过 effect_id 引用

剪映内置特效/转场的 resource_id 是固定的字符串 ID，可以通过用户在剪映里
手动加一次后从 draft 中读出。本模块提供常用 preset 的 ID 表。
"""
from __future__ import annotations

from typing import Optional

from .draft import Draft, _new_id


# 常用转场 resource_id（剪映 5.x）
# 这些 ID 是剪映内置转场的标识，可通过用户手动添加一次后从 draft 读出
TRANSITION_PRESETS = {
    "fade": "transition.fade_in_out",          # 淡入淡出
    "slide_left": "transition.slide_left",     # 向左滑动
    "slide_right": "transition.slide_right",
    "slide_up": "transition.slide_up",
    "slide_down": "transition.slide_down",
    "zoom_in": "transition.zoom_in",
    "zoom_out": "transition.zoom_out",
    "rotate": "transition.rotate",
    "blur": "transition.blur",
    "flash": "transition.flash",
    "glitch": "transition.glitch",
    "whip_pan": "transition.whip_pan",
}

# 常用视频特效 resource_id
EFFECT_PRESETS = {
    "vignette": "effect.vignette",             # 暗角
    "sharpen": "effect.sharpen",               # 锐化
    "blur": "effect.blur",                     # 模糊
    "glow": "effect.glow",                     # 发光
    "noise": "effect.noise",                   # 噪点
    "mirror": "effect.mirror",
    "edge_extend": "effect.edge_extend",
    "vhs": "effect.vhs",
    "film_grain": "effect.film_grain",
    "color_correction": "effect.color_correction",
}

# 常用调色 LUT（应用 .cube 文件）
LUT_PRESETS = {
    "cinematic": "lut.cinematic",
    "warm": "lut.warm",
    "cool": "lut.cool",
    "noir": "lut.noir",
    "vintage": "lut.vintage",
}


# ---------------------------------------------------------------------------
# 转场
# ---------------------------------------------------------------------------

def add_transition(draft: Draft, track_id: str,
                   between_segment_left: str,
                   between_segment_right: str,
                   preset: str = "fade",
                   duration_us: int = 500_000,
                   overlap: bool = True) -> str:
    """在两个相邻 segment 之间加转场。

    - preset: TRANSITION_PRESETS 中的 key
    - duration_us: 转场时长（默认 0.5s）
    - overlap: True 时转场覆盖两段重叠区，False 时仅前段尾部
    """
    if preset not in TRANSITION_PRESETS:
        raise KeyError(f"未知转场 preset: {preset}。可用: {list(TRANSITION_PRESETS)}")

    resource_id = TRANSITION_PRESETS[preset]
    trans_id = _new_id()

    transition = {
        "id": trans_id,
        "type": "transition",
        "duration": duration_us,
        "left_segment_id": between_segment_left,
        "right_segment_id": between_segment_right,
        "transition": {
            "resource_id": resource_id,
            "name": preset,
            "category_name": "basic",
            "category_id": "",
            "request_id": "",
            "is_affect_video": True,
            "is_affect_audio": False,
            "duration": duration_us,
            "overlap": overlap,
            "render_index": 0,
            "direction": 0,
            "apply_id": 0,
            "params": [],
        },
        "extra_material_refs": [],
    }

    # 找到 track 并把 transition 加入
    for t in draft.tracks_raw:
        if t.get("id") == track_id:
            t.setdefault("transitions", []).append(transition)
            break
    else:
        raise KeyError(f"track {track_id} 不存在")

    draft._modified = True
    return trans_id


def add_transition_simple(draft: Draft, track_id: str,
                          at_index: int,
                          preset: str = "fade",
                          duration_us: int = 500_000) -> str:
    """简化版：在 track 上第 at_index 个与第 at_index+1 个 segment 之间加转场。"""
    track = draft.get_track(track_id)
    if at_index < 0 or at_index + 1 >= len(track.segments):
        raise IndexError(f"at_index {at_index} 越界（track 共 {len(track.segments)} 段）")
    left = track.segments[at_index]
    right = track.segments[at_index + 1]
    return add_transition(draft, track_id, left.id, right.id, preset, duration_us)


# ---------------------------------------------------------------------------
# 视频特效
# ---------------------------------------------------------------------------

def add_video_effect(draft: Draft, segment_id: str,
                     preset: str = "vignette",
                     intensity: float = 1.0,
                     track_id: Optional[str] = None) -> str:
    """给某个 segment 加视频特效。

    实际上剪映的特效是"特效轨道"（type=effect）上的 segment，
    通过 keyframe_refs 或 effect 字段关联到目标 segment。
    本实现采用简化的 effect segment 模型。
    """
    if preset not in EFFECT_PRESETS:
        raise KeyError(f"未知特效 preset: {preset}")

    target_seg = draft.get_segment_raw(segment_id)
    if not target_seg:
        raise KeyError(f"segment {segment_id} 不存在")

    # 在 materials.effects 中添加特效资源
    effect_mat_id = _new_id()
    effect_mat = {
        "id": effect_mat_id,
        "type": "effect",
        "resource_id": EFFECT_PRESETS[preset],
        "name": preset,
        "category_name": "video_effect",
        "category_id": "",
        "request_id": "",
        "is_affect_video": True,
        "is_affect_audio": False,
        "is_valid": True,
        "is_collection": False,
        "is_tone_adjust": False,
        "matrix": {"x": 0, "y": 0},
        "path": "",
        "platform": "",
        "search_id": "",
        "source_platform": 0,
        "stable_material_id": effect_mat_id,
        "team_id": "",
        "text_id": "",
        "version": "",
    }
    draft.add_material("effect", effect_mat)

    # 找或创建 effect track
    if track_id is None:
        ets = draft.effect_tracks
        if ets:
            track_id = ets[0].id
        else:
            track_id = draft.add_track("effect")

    # effect segment 与目标 segment 时间一致
    tt = target_seg.get("target_timerange", {})
    seg = {
        "id": _new_id(),
        "material_id": effect_mat_id,
        "source_timerange": {"start": 0, "duration": tt.get("duration", 0)},
        "target_timerange": tt,
        "source_in_speed": 1.0,
        "speed": 1.0,
        "volume": 1.0,
        "common_keyframes": [],
        "enabled": True,
        "render_index": 0,
        "track_id": track_id,
        "visible": True,
        "is_placeholder": False,
        "extra_material_refs": [effect_mat_id],  # 引用自身的 material_id（与 LUT 模式一致）
        "effect_intensity": intensity,
        "fursuer_effect": [],
    }
    sid = draft.add_segment_raw(track_id, seg)

    # 在目标 segment 上追加 effect material 引用（这样剪映才能把特效关联到目标片段）
    target_refs = target_seg.setdefault("extra_material_refs", [])
    target_refs.append(effect_mat_id)

    draft._modified = True
    return sid


# ---------------------------------------------------------------------------
# 调色 LUT
# ---------------------------------------------------------------------------

def apply_lut(draft: Draft, segment_id: str, lut_path_or_preset: str,
              intensity: float = 1.0) -> str:
    """应用调色 LUT。

    lut_path_or_preset: .cube 文件绝对路径，或 LUT_PRESETS 的 key。
    """
    if lut_path_or_preset in LUT_PRESETS:
        resource_id = LUT_PRESETS[lut_path_or_preset]
        path = ""
    else:
        resource_id = "lut.custom"
        path = lut_path_or_preset

    target_seg = draft.get_segment_raw(segment_id)
    if not target_seg:
        raise KeyError(f"segment {segment_id} 不存在")

    lut_mat_id = _new_id()
    lut_mat = {
        "id": lut_mat_id,
        "type": "lut",
        "resource_id": resource_id,
        "path": path,
        "name": "LUT",
        "intensity": intensity,
        "is_valid": True,
    }
    # LUT 也放在 effects 桶
    draft.add_material("effect", lut_mat)

    # 把 lut 应用到目标 segment 的 extra_material_refs
    refs = target_seg.setdefault("extra_material_refs", [])
    refs.append(lut_mat_id)
    draft._modified = True
    return lut_mat_id


# ---------------------------------------------------------------------------
# 关键帧动画
# ---------------------------------------------------------------------------

def add_keyframe(draft: Draft, segment_id: str,
                 at_us: int, value: float,
                 field: str = "scale",
                 easing: str = "linear") -> None:
    """给 segment 加关键帧。

    field ∈ {"scale", "scale_x", "scale_y", "rotation", "position_x", "position_y", "alpha", "volume"}
    """
    raw = draft.get_segment_raw(segment_id)
    if not raw:
        raise KeyError(f"segment {segment_id} 不存在")

    kf = {
        "id": _new_id(),
        "field": field,
        "time": at_us,
        "value": value,
        "easing": easing,
        "curve_type": 0,
        "default": False,
    }
    raw.setdefault("common_keyframes", []).append(kf)
    raw["common_keyframes"].sort(key=lambda k: k["time"])
    draft._modified = True


def add_fade_in(draft: Draft, segment_id: str, duration_us: int = 500_000) -> None:
    """片段淡入（alpha 0→1）。"""
    raw = draft.get_segment_raw(segment_id)
    if not raw:
        raise KeyError(segment_id)
    start = raw.get("target_timerange", {}).get("start", 0)
    add_keyframe(draft, segment_id, start, 0.0, field="alpha")
    add_keyframe(draft, segment_id, start + duration_us, 1.0, field="alpha")


def add_fade_out(draft: Draft, segment_id: str, duration_us: int = 500_000) -> None:
    """片段淡出（alpha 1→0）。"""
    raw = draft.get_segment_raw(segment_id)
    if not raw:
        raise KeyError(segment_id)
    tt = raw.get("target_timerange", {})
    end = tt.get("start", 0) + tt.get("duration", 0)
    add_keyframe(draft, segment_id, end - duration_us, 1.0, field="alpha")
    add_keyframe(draft, segment_id, end, 0.0, field="alpha")
