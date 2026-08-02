"""cut.jianying.text — 字幕与文本添加。

剪映文本结构：
- material 在 materials.texts 数组，含 content/text_style/text_size 等
- segment 在 type=text 的 track 上
- 一个 text segment 通常没有 source_timerange，只有 target_timerange

文本素材字段较复杂，本模块封装常用场景：
- add_title: 标题（屏幕中央大字）
- add_subtitle: 字幕（屏幕底部小字）
- add_text: 自定义文本（完全自定义位置/样式）
"""
from __future__ import annotations

import copy
from typing import Optional, Dict, Any, Union

from .draft import Draft, _new_id, _us


# 文本样式预设
TEXT_PRESETS = {
    "title": {
        "text_size": 80,
        "text_color": "#FFFFFF",
        "background_color": "#00000000",
        "background_alpha": 0.0,
        "text_alpha": 1.0,
        "alignment": 1,  # 居中
        "position_x": 0.0,
        "position_y": -0.3,  # 偏上
        "font_path": "",
        "font_resource_id": "",
        "font_id": "",
        "font_size": 80,
        "text_stroke_color": "#000000",
        "text_stroke_width": 0,
        "text_shadow_color": "#000000",
        "text_shadow_alpha": 0,
        "text_shadow_color_v2": "",
        "text_shadow_point": {"x": 0, "y": 0},
        "text_shadow_radius": 0,
    },
    "subtitle": {
        "text_size": 40,
        "text_color": "#FFFFFF",
        "background_color": "#000000",
        "background_alpha": 0.5,
        "text_alpha": 1.0,
        "alignment": 1,
        "position_x": 0.0,
        "position_y": 0.4,  # 偏下
        "font_path": "",
        "font_resource_id": "",
        "font_id": "",
        "font_size": 40,
        "text_stroke_color": "#000000",
        "text_stroke_width": 1,
        "text_shadow_color": "#000000",
        "text_shadow_alpha": 0.5,
        "text_shadow_color_v2": "#000000",
        "text_shadow_point": {"x": 0.0, "y": 0.06},
        "text_shadow_radius": 1.0,
    },
}


def _make_text_material(content: str, preset: str = "subtitle",
                        style_overrides: Optional[Dict] = None) -> Dict[str, Any]:
    """构造一个 text material。"""
    preset_style = copy.deepcopy(TEXT_PRESETS.get(preset, TEXT_PRESETS["subtitle"]))
    if style_overrides:
        preset_style.update(style_overrides)

    mat_id = _new_id()
    # 剪映 text material 核心字段
    return {
        "id": mat_id,
        "type": "subtitle" if preset == "subtitle" else "title",
        "text": content,
        "content": content,
        "duration": 3_000_000,  # 默认 3 秒，由 segment 决定实际时长
        "text_styles": [{
            "text": content,
            "style": preset_style,
        }],
        "text_color": preset_style.get("text_color", "#FFFFFF"),
        "text_size": preset_style.get("text_size", 40),
        "background_color": preset_style.get("background_color", "#000000"),
        "background_alpha": preset_style.get("background_alpha", 0.0),
        "font_path": preset_style.get("font_path", ""),
        "font_resource_id": preset_style.get("font_resource_id", ""),
        "font_id": preset_style.get("font_id", ""),
        "font_size": preset_style.get("font_size", 40),
        "font_team_id": "",
        "text_stroke_color": preset_style.get("text_stroke_color", "#000000"),
        "text_stroke_width": preset_style.get("text_stroke_width", 0),
        "text_shadow_color": preset_style.get("text_shadow_color", "#000000"),
        "text_shadow_alpha": preset_style.get("text_shadow_alpha", 0),
        "text_shadow_color_v2": preset_style.get("text_shadow_color_v2", ""),
        "text_shadow_point": preset_style.get("text_shadow_point", {"x": 0, "y": 0}),
        "text_shadow_radius": preset_style.get("text_shadow_radius", 0),
        "alignment": preset_style.get("alignment", 1),
        "base_content": content,
        "combination_id": "",
        "content_id": _new_id(),
        "create_time": 0,
        "extra_resource_id": "",
        "is_rich_text": False,
        "language": "",
        "local_material_id": mat_id,
        "md5": "",
        "multi_language_current": "",
        "name": "",
        "paragraphs": [],
        "recognition_id": "",
        "recognition_task_id": "",
        "source": 0,
        "text_edit": False,
        "text_preset_resource_id": "",
        "text_source": "",
        "text_team_id": "",
        "text_type": preset,
        "text_underline": False,
        "style_name": "",
        "style_id": "",
        "italic": False,
        "bold": False,
        "underline": False,
        "is_combination": False,
        "is_recognize": False,
        "is_sentence_template": False,
        "is_template": False,
        "recognize_type": 0,
        "wave_form": [],
        "create_segment": True,
        "sort_words": [],
        "initial_scale": 1.0,
        "transform": {"x": preset_style.get("position_x", 0), "y": preset_style.get("position_y", 0)},
        "scale": {"x": 1.0, "y": 1.0},
        "background_style": {
            "background_alpha": preset_style.get("background_alpha", 0),
            "background_color": preset_style.get("background_color", "#000000"),
            "background_height": 0,
            "background_width": 0,
            "background_radius": 0,
            "background_shape": 0,
        },
        "font_size_follow_scale": False,
        "fixed_height": 0,
        "fixed_width": 0,
        "global_alpha": 1.0,
        "text_curve": 0,
        "text_curve_x": 0,
        "text_curve_y": 0,
        "shadow_point": {"x": 0, "y": 0},
        "text_alignment": preset_style.get("alignment", 1),
        "line_feed": 0,
        "line_spacing": 1.0,
        "letter_spacing": 0.0,
        "use_effect": False,
        "default_effect": {},
        "initial_scale_x": 1.0,
        "initial_scale_y": 1.0,
        "initial_scale_z": 1.0,
        "sample_sentence": "",
    }


def add_text(draft: Draft, content: str,
             start_us: Union[int, float, str],
             duration_us: Union[int, float, str] = 3_000_000,
             track_id: Optional[str] = None,
             preset: str = "subtitle",
             style_overrides: Optional[Dict] = None,
             unit: str = "us") -> str:
    """添加文本片段。

    - preset: "title" / "subtitle" / 自定义
    - style_overrides: 覆盖预设样式，如 {"text_color": "#FF0000"}
    返回 segment_id。
    """
    mat = _make_text_material(content, preset=preset, style_overrides=style_overrides)
    mat_id = draft.add_material("text", mat)

    if track_id is None:
        tts = draft.text_tracks
        if tts:
            track_id = tts[0].id
        else:
            track_id = draft.add_track("text")

    start = _us(start_us, unit)
    dur = _us(duration_us, unit)

    seg = {
        "id": _new_id(),
        "material_id": mat_id,
        "source_timerange": {"start": 0, "duration": dur},
        "target_timerange": {"start": start, "duration": dur},
        "source_in_speed": 1.0,
        "speed": 1.0,
        "volume": 1.0,
        "common_keyframes": [],
        "material_animations": [],
        "enabled": True,
        "render_index": 0,
        "track_id": track_id,
        "visible": True,
        "is_placeholder": False,
        "clip": {
            "alpha": 1.0,
            "flip": {"horizontal": False, "vertical": False},
            "rotation": 0,
            "scale": {"x": 1.0, "y": 1.0},
            "transform": {
                "x": mat["transform"]["x"],
                "y": mat["transform"]["y"],
            },
        },
        "extra_material_refs": [],
        "fursuer_effect": [],
        "reverse": False,
        "source": 0,
        "stage_width": 0,
        "stage_height": 0,
    }
    seg_id = draft.add_segment_raw(track_id, seg)
    draft.extend_duration()
    return seg_id


def add_title(draft: Draft, content: str,
              start_us: Union[int, float, str],
              duration_us: Union[int, float, str] = 3_000_000,
              **kwargs) -> str:
    """添加标题（屏幕中上方大字）。"""
    return add_text(draft, content, start_us, duration_us, preset="title", **kwargs)


def add_subtitle(draft: Draft, content: str,
                 start_us: Union[int, float, str],
                 duration_us: Union[int, float, str] = 3_000_000,
                 **kwargs) -> str:
    """添加字幕（屏幕底部小字，带半透明黑底）。"""
    return add_text(draft, content, start_us, duration_us, preset="subtitle", **kwargs)


def add_subtitles_batch(draft: Draft, subtitles: list,
                        track_id: Optional[str] = None,
                        preset: str = "subtitle") -> list:
    """批量添加字幕。

    subtitles: [{"text": "...", "start_us": 0, "duration_us": 2000000}, ...]
    返回 [segment_id, ...]
    """
    ids = []
    for s in subtitles:
        sid = add_text(
            draft, s["text"], s["start_us"], s.get("duration_us", 3_000_000),
            track_id=track_id, preset=preset,
            style_overrides=s.get("style_overrides"),
        )
        ids.append(sid)
    return ids


def update_text_content(draft: Draft, segment_id: str, new_content: str) -> None:
    """修改已有文本片段的内容。"""
    from .draft import SegmentNotFoundError
    raw = draft.get_segment_raw(segment_id)
    if not raw:
        raise SegmentNotFoundError(segment_id)
    mat = draft.find_material(raw.get("material_id", ""))
    if not mat:
        return
    mat["text"] = new_content
    mat["content"] = new_content
    mat["base_content"] = new_content
    if mat.get("text_styles"):
        mat["text_styles"][0]["text"] = new_content
    draft._modified = True
