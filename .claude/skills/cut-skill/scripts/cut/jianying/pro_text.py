"""cut.jianying.pro_text — 专业字幕与文字库。

基于剪映大神字幕技巧调研：
- 花字预设（10种带动画样式）
- 顺序入场动画
- ASR 自动字幕（whisper 集成）
- 浮空滤色文字
- 批量字幕样式应用
- 文字跟踪（基础版）
"""
from __future__ import annotations

import copy
import sys
from typing import Optional, Dict, Any, List, Union

from .draft import Draft, _new_id, _us, _hms
from .text import add_text
from .effects import add_keyframe


HUAZI_PRESETS = {
    "hook_red": {
        "text_size": 100, "text_color": "#FF3030",
        "text_stroke_color": "#FFFFFF", "text_stroke_width": 4,
        "background_alpha": 0.0,
        "text_shadow_color": "#000000", "text_shadow_alpha": 0.8,
        "text_shadow_radius": 2.0, "font_size": 100, "position_y": -0.3,
        "animation_in": "bounce", "animation_in_duration": 500_000,
    },
    "hook_yellow": {
        "text_size": 90, "text_color": "#FFD700",
        "text_stroke_color": "#000000", "text_stroke_width": 5,
        "background_alpha": 0.0,
        "text_shadow_color": "#FF6600", "text_shadow_alpha": 0.9,
        "text_shadow_radius": 3.0, "font_size": 90, "position_y": -0.3,
        "animation_in": "zoom", "animation_in_duration": 400_000,
    },
    "vlog_clean": {
        "text_size": 42, "text_color": "#FFFFFF",
        "text_stroke_color": "#000000", "text_stroke_width": 2,
        "background_color": "#000000", "background_alpha": 0.4,
        "text_shadow_color": "#000000", "text_shadow_alpha": 0.5,
        "text_shadow_radius": 1.0, "font_size": 42, "position_y": 0.42,
        "alignment": 1, "animation_in": "fade", "animation_in_duration": 300_000,
    },
    "vlog_minimal": {
        "text_size": 36, "text_color": "#FFFFFF", "text_stroke_width": 0,
        "background_alpha": 0.0,
        "text_shadow_color": "#000000", "text_shadow_alpha": 0.6,
        "text_shadow_radius": 1.5, "font_size": 36, "position_y": 0.45,
        "alignment": 1, "animation_in": "fade", "animation_in_duration": 200_000,
    },
    "tutorial_boxed": {
        "text_size": 40, "text_color": "#FFFFFF", "text_stroke_width": 0,
        "background_color": "#1A1A1A", "background_alpha": 0.85,
        "font_size": 40, "position_y": 0.4, "alignment": 1,
        "animation_in": "slide_up", "animation_in_duration": 250_000,
    },
    "cinematic": {
        "text_size": 38, "text_color": "#E8E8E8", "text_stroke_width": 0,
        "background_alpha": 0.0,
        "text_shadow_color": "#000000", "text_shadow_alpha": 0.7,
        "text_shadow_radius": 2.0, "font_size": 38, "position_y": 0.45,
        "alignment": 1, "animation_in": "fade", "animation_in_duration": 500_000,
    },
    "emphasis_red": {
        "text_size": 80, "text_color": "#FF1744",
        "text_stroke_color": "#FFFFFF", "text_stroke_width": 3,
        "background_alpha": 0.0,
        "text_shadow_color": "#000000", "text_shadow_alpha": 0.5,
        "font_size": 80, "position_y": -0.2,
        "animation_in": "pop", "animation_in_duration": 300_000,
    },
    "stat_number": {
        "text_size": 120, "text_color": "#00E5FF",
        "text_stroke_color": "#000000", "text_stroke_width": 2,
        "background_alpha": 0.0,
        "text_shadow_color": "#00E5FF", "text_shadow_alpha": 0.6,
        "text_shadow_radius": 4.0, "font_size": 120, "position_y": 0.0,
        "alignment": 1, "animation_in": "count", "animation_in_duration": 800_000,
    },
    "quote_italic": {
        "text_size": 34, "text_color": "#B0B0B0", "text_stroke_width": 0,
        "background_alpha": 0.0, "font_size": 34, "position_y": 0.3,
        "alignment": 1, "italic": True,
        "animation_in": "fade", "animation_in_duration": 600_000,
    },
    "chapter_title": {
        "text_size": 72, "text_color": "#FFFFFF", "text_stroke_width": 0,
        "background_alpha": 0.0,
        "text_shadow_color": "#000000", "text_shadow_alpha": 0.8,
        "text_shadow_radius": 3.0, "font_size": 72, "position_y": 0.0,
        "alignment": 1, "bold": True,
        "animation_in": "slide_left", "animation_in_duration": 500_000,
    },
}

ANIMATION_RESOURCES = {
    "fade": "animation.fade_in", "bounce": "animation.bounce_in",
    "zoom": "animation.zoom_in", "pop": "animation.pop_in",
    "slide_up": "animation.slide_up_in", "slide_down": "animation.slide_down_in",
    "slide_left": "animation.slide_left_in", "slide_right": "animation.slide_right_in",
    "count": "animation.count_up", "typewriter": "animation.typewriter",
}


def add_huazi_text(draft, content, start_us, duration_us=3_000_000,
                   preset="vlog_clean", track_id=None, overrides=None):
    """添加花字文本（带预设动画与样式）。"""
    if preset not in HUAZI_PRESETS:
        raise KeyError(f"未知花字预设: {preset}. 可选: {list(HUAZI_PRESETS)}")

    style = copy.deepcopy(HUAZI_PRESETS[preset])
    if overrides:
        style.update(overrides)

    anim_in = style.pop("animation_in", None)
    anim_dur = style.pop("animation_in_duration", 300_000)

    seg_id = add_text(
        draft, content, start_us, duration_us,
        track_id=track_id,
        preset="subtitle" if style.get("position_y", 0) > 0 else "title",
        style_overrides=style,
    )

    if anim_in and anim_in in ANIMATION_RESOURCES:
        _apply_text_animation(draft, seg_id, anim_in, anim_dur, "in")

    return {"segment_id": seg_id, "preset": preset, "animation": anim_in}


def _apply_text_animation(draft, segment_id, anim_type, duration_us, phase="in"):
    """给文本 segment 添加入场/出场动画。"""
    raw = draft.get_segment_raw(segment_id)
    if not raw:
        return

    resource_id = ANIMATION_RESOURCES.get(anim_type)
    if not resource_id:
        return

    anim_id = _new_id()
    animation = {
        "id": anim_id, "type": phase, "duration": duration_us,
        "resource_id": resource_id, "name": anim_type,
        "category_id": phase, "request_id": "", "platform": "",
    }

    anims = raw.setdefault("material_animations", [])
    anims.append(animation)
    draft._modified = True


def add_sequential_text(draft, text, start_us, per_char_duration_us=80_000,
                        preset="vlog_clean", track_id=None):
    """顺序入场字幕：每个字依次出现（打字机效果）。"""
    start = _us(start_us)
    seg_ids = []
    for i, char in enumerate(text):
        if char.isspace():
            continue
        char_start = start + i * per_char_duration_us
        sid = add_huazi_text(draft, char, char_start, per_char_duration_us * 2,
                            preset=preset, track_id=track_id)
        seg_ids.append(sid["segment_id"])
    return seg_ids


def auto_subtitle_from_audio(draft, audio_segment_id, engine="mock",
                             language="zh", preset="vlog_clean"):
    """从音频 segment 自动生成字幕。"""
    audio_raw = draft.get_segment_raw(audio_segment_id)
    if not audio_raw:
        raise KeyError(f"audio segment {audio_segment_id} 不存在")

    tt = audio_raw.get("target_timerange", {})
    audio_start = int(tt.get("start", 0))
    audio_dur = int(tt.get("duration", 0))

    if engine == "whisper":
        segments = _asr_whisper(audio_raw.get("material_id"), draft, language)
    elif engine == "online":
        segments = _asr_online(audio_raw.get("material_id"), draft, language)
    else:
        segments = _asr_mock(audio_start, audio_dur)

    added = []
    for seg in segments:
        result = add_huazi_text(draft, seg["text"], start_us=seg["start_us"],
                               duration_us=seg["duration_us"], preset=preset)
        added.append(result["segment_id"])

    return {"subtitles": segments, "added": len(added), "segment_ids": added, "engine": engine}


def _asr_mock(start_us, duration_us):
    """Mock ASR：返回假的字幕段。"""
    sample_texts = [
        "大家好 欢迎来到我的频道",
        "今天我们来聊聊 AI 编程",
        "首先 让我们看看 cut.skill 是什么",
        "它可以让 agent 操控剪映和 Premiere",
        "感谢观看 我们下期再见",
    ]
    seg_dur = duration_us // len(sample_texts) if duration_us > 0 else 1_000_000
    return [
        {"text": t, "start_us": start_us + i * seg_dur, "duration_us": seg_dur}
        for i, t in enumerate(sample_texts)
    ]


def _asr_whisper(material_id, draft, language):
    """用 openai-whisper 做 ASR。"""
    try:
        import whisper
    except ImportError:
        print("whisper 未安装，回退到 mock", file=sys.stderr)
        return _asr_mock(0, 5_000_000)

    mat = draft.find_material(material_id) if material_id else None
    if not mat or not mat.get("path"):
        return _asr_mock(0, 5_000_000)

    model = whisper.load_model("base")
    result = model.transcribe(mat["path"], language=language if language != "auto" else None)
    return [
        {"text": seg["text"].strip(),
         "start_us": int(seg["start"] * 1_000_000),
         "duration_us": int((seg["end"] - seg["start"]) * 1_000_000)}
        for seg in result["segments"]
    ]


def _asr_online(material_id, draft, language):
    """在线 ASR API（占位）。"""
    return _asr_mock(0, 5_000_000)


def add_overlay_blend_text(draft, content, start_us, duration_us=3_000_000,
                           blend_mode="screen", text_color="#FFFFFF",
                           font_size=60, position_y=0.0, track_id=None):
    """浮空滤色文字：用混合模式让文字与背景融合。"""
    style = {
        "text_color": text_color, "text_size": font_size, "font_size": font_size,
        "background_alpha": 0.0, "position_y": position_y, "alignment": 1,
    }
    seg_id = add_text(draft, content, start_us, duration_us,
                     track_id=track_id, preset="title", style_overrides=style)

    raw = draft.get_segment_raw(seg_id)
    if raw:
        raw["blend_mode"] = blend_mode
        draft._modified = True

    return seg_id


def batch_apply_subtitle_style(draft, preset="vlog_clean", track_id=None):
    """批量给已有字幕应用花字预设样式。"""
    if preset not in HUAZI_PRESETS:
        raise KeyError(f"未知预设: {preset}")

    style = copy.deepcopy(HUAZI_PRESETS[preset])
    style.pop("animation_in", None)
    style.pop("animation_in_duration", None)

    count = 0
    for track in draft.text_tracks:
        if track_id and track.id != track_id:
            continue
        for seg in track.segments:
            mat = draft.find_material(seg.material_id)
            if not mat:
                continue
            for k, v in style.items():
                if k == "position_y":
                    mat.setdefault("transform", {})["y"] = v
                elif k == "alignment":
                    mat["alignment"] = v
                elif k in ("bold", "italic", "underline"):
                    mat[k] = v
                else:
                    mat[k] = v
            if mat.get("text_styles"):
                mat["text_styles"][0]["style"].update(style)
            count += 1

    draft._modified = True
    return {"applied": count, "preset": preset}


def add_tracking_text(draft, content, target_segment_id, duration_us,
                      offset_x=0.1, offset_y=-0.2, font_size=40, track_id=None):
    """文字跟踪：让文字跟随目标 segment 的位置变化。"""
    target_raw = draft.get_segment_raw(target_segment_id)
    if not target_raw:
        raise KeyError(f"target segment {target_segment_id} 不存在")

    tt = target_raw.get("target_timerange", {})
    target_start = int(tt.get("start", 0))
    target_dur = int(tt.get("duration", 0))

    style = {
        "text_color": "#FFFFFF", "text_size": font_size, "font_size": font_size,
        "background_color": "#000000", "background_alpha": 0.6,
        "text_stroke_width": 1, "position_y": offset_y,
    }
    seg_id = add_text(draft, content, target_start,
                     min(_us(duration_us), target_dur),
                     track_id=track_id, preset="subtitle", style_overrides=style)

    target_kfs = target_raw.get("common_keyframes", [])
    pos_kfs = [kf for kf in target_kfs if kf.get("field") in ("position_x", "position_y")]
    text_raw = draft.get_segment_raw(seg_id)
    if text_raw:
        for kf in pos_kfs:
            kf_copy = copy.deepcopy(kf)
            kf_copy["id"] = _new_id()
            if kf_copy["field"] == "position_x":
                kf_copy["value"] = float(kf_copy["value"]) + offset_x
            elif kf_copy["field"] == "position_y":
                kf_copy["value"] = float(kf_copy["value"]) + offset_y
            text_raw.setdefault("common_keyframes", []).append(kf_copy)
        draft._modified = True

    return seg_id
