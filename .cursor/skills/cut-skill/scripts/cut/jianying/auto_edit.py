"""cut.jianying.auto_edit — 一键成片引擎。

整合所有专业能力：
1. 素材智能筛选
2. 自动卡点（基于 BGM 节拍）
3. ASR 自动字幕
4. 自动调色
5. 自动加转场
6. 自动混音（BGM ducking）

支持两种模式：
- auto_edit: 从零生成（给定素材+模板）
- imitate_viral: 模仿爆款（给定参考视频元数据）
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List

from .draft import Draft, _new_id, _us, _hms
from . import materials, segments, text, effects, audio
from .pro_effects import apply_pro_transition
from .pro_text import add_huazi_text, auto_subtitle_from_audio
from .pro_color import apply_color_preset
from .viral_templates import apply_viral_template, VIRAL_TEMPLATES
from .audio_beat import detect_beats, beat_sync_segments


def select_best_clips(material_ids, target_duration_us, draft=None):
    """从素材池中智能筛选最佳片段。"""
    clips = []
    for mid in material_ids:
        mat = None
        if draft:
            mat = draft.find_material(mid)
        duration = int(mat.get("duration", 0)) if mat else 0
        clips.append({"id": mid, "duration": duration})

    clips.sort(key=lambda c: c["duration"], reverse=True)

    selected = []
    accumulated = 0
    for c in clips:
        if accumulated >= target_duration_us:
            break
        selected.append(c["id"])
        accumulated += c["duration"]

    return {"selected": selected, "count": len(selected),
            "total_duration_us": accumulated, "target_duration_us": target_duration_us}


def auto_edit(draft, video_material_ids, bgm_material_id=None,
              template="vlog", texts=None,
              auto_subtitle=True, auto_color=True, auto_transition=True,
              beat_sync=False, color_preset=None, subtitle_engine="mock"):
    """一键成片主入口。"""
    report = {"template": template, "steps": [], "errors": []}

    # Step 1: 应用模板
    try:
        tmpl_result = apply_viral_template(
            draft, template, video_material_ids,
            bgm_material_id=bgm_material_id, texts=texts,
            auto_color=False, auto_transition=False,
        )
        report["steps"].append({"step": "template", "status": "ok", "detail": tmpl_result})
        seg_ids = tmpl_result["segment_ids"]
    except Exception as e:
        report["errors"].append({"step": "template", "error": str(e)})
        return report

    # Step 2: 自动转场
    if auto_transition:
        try:
            cfg = VIRAL_TEMPLATES[template]
            transitions = cfg.get("transitions", [])
            transition_preset_map = {
                "fade": "smooth", "smooth": "smooth",
                "flash_white": "flash_white", "flash_black": "flash_black",
                "zoom_in": "zoom_in", "zoom_out": "zoom_out",
                "motion_blur": "motion_blur",
            }
            count = 0
            for i, trans_key in enumerate(transitions):
                if i + 1 >= len(seg_ids):
                    break
                try:
                    preset = transition_preset_map.get(trans_key, "smooth")
                    apply_pro_transition(draft, seg_ids[i], seg_ids[i+1], preset=preset)
                    count += 1
                except Exception:
                    pass
            report["steps"].append({"step": "transitions", "status": "ok", "count": count})
        except Exception as e:
            report["errors"].append({"step": "transitions", "error": str(e)})

    # Step 3: 自动调色
    if auto_color:
        try:
            preset = color_preset or VIRAL_TEMPLATES[template].get("color_preset", "teal_orange")
            applied = 0
            for sid in seg_ids:
                try:
                    apply_color_preset(draft, sid, preset, intensity=0.8)
                    applied += 1
                except Exception:
                    pass
            report["steps"].append({"step": "color", "status": "ok",
                                    "preset": preset, "applied": applied})
        except Exception as e:
            report["errors"].append({"step": "color", "error": str(e)})

    # Step 4: 节拍卡点
    if beat_sync and bgm_material_id:
        try:
            bgm_sid = None
            for track in draft.audio_tracks:
                for seg in track.segments:
                    if seg.material_id == bgm_material_id:
                        bgm_sid = seg.id
                        break
                if bgm_sid:
                    break

            if bgm_sid:
                beat_result = beat_sync_segments(draft, bgm_sid, seg_ids)
                report["steps"].append({"step": "beat_sync", "status": "ok", "detail": beat_result})
        except Exception as e:
            report["errors"].append({"step": "beat_sync", "error": str(e)})

    # Step 5: ASR 自动字幕
    if auto_subtitle and seg_ids:
        try:
            first_seg = seg_ids[0]
            sub_result = auto_subtitle_from_audio(
                draft, first_seg, engine=subtitle_engine, language="zh",
                preset="vlog_clean",
            )
            report["steps"].append({"step": "subtitle", "status": "ok",
                                    "engine": subtitle_engine, "added": sub_result["added"]})
        except Exception as e:
            report["errors"].append({"step": "subtitle", "error": str(e)})

    # Step 6: BGM ducking
    if bgm_material_id:
        try:
            bgm_sid = None
            for track in draft.audio_tracks:
                for seg in track.segments:
                    if seg.material_id == bgm_material_id:
                        bgm_sid = seg.id
                        break
                if bgm_sid:
                    break

            if bgm_sid:
                voice_ids = []
                for track in draft.text_tracks:
                    for seg in track.segments:
                        voice_ids.append(seg.id)
                if voice_ids:
                    audio.apply_ducking(draft, voice_ids, bgm_sid,
                                       duck_level=0.3, fade_us=200_000)
                    report["steps"].append({"step": "ducking", "status": "ok",
                                            "voice_segments": len(voice_ids)})
        except Exception as e:
            report["errors"].append({"step": "ducking", "error": str(e)})

    report["total_duration_us"] = draft.duration
    report["total_duration_hms"] = draft.duration_hms
    report["success"] = len(report["errors"]) == 0
    return report


def imitate_viral(draft, reference, video_material_ids, bgm_material_id=None):
    """模仿爆款视频生成同类型视频。

    reference 包含：template, duration_us, bpm, color_preset, texts, subtitle_engine
    """
    template = reference.get("template", "vlog")
    if template not in VIRAL_TEMPLATES:
        raise KeyError(f"参考视频用了未知模板: {template}")

    target_total = reference.get("duration_us")
    if target_total:
        video_material_ids = _scale_to_duration(
            draft, video_material_ids, target_total, template
        )

    return auto_edit(
        draft, video_material_ids,
        bgm_material_id=bgm_material_id, template=template,
        texts=reference.get("texts"),
        auto_subtitle=reference.get("auto_subtitle", True),
        auto_color=True, auto_transition=True,
        beat_sync=reference.get("bpm") is not None,
        color_preset=reference.get("color_preset"),
        subtitle_engine=reference.get("subtitle_engine", "mock"),
    )


def _scale_to_duration(draft, material_ids, target_us, template):
    """根据目标时长调整素材列表。"""
    cfg = VIRAL_TEMPLATES[template]
    n_phases = len(cfg["structure"])
    if len(material_ids) < n_phases:
        material_ids = (material_ids * (n_phases // len(material_ids) + 1))[:n_phases]
    return material_ids


BGM_RECOMMENDATIONS = {
    "tutorial": {"mood": "upbeat", "bpm_range": (90, 120), "volume": 0.2},
    "review": {"mood": "professional", "bpm_range": (80, 110), "volume": 0.25},
    "vlog": {"mood": "chill", "bpm_range": (70, 100), "volume": 0.3},
    "knowledge": {"mood": "focus", "bpm_range": (80, 110), "volume": 0.2},
    "drama": {"mood": "emotional", "bpm_range": (60, 90), "volume": 0.4},
    "comparison": {"mood": "energetic", "bpm_range": (100, 130), "volume": 0.25},
    "emotional": {"mood": "melancholy", "bpm_range": (60, 80), "volume": 0.45},
    "beat_sync": {"mood": "energetic", "bpm_range": (120, 140), "volume": 0.35},
}


def recommend_bgm(template):
    """根据模板推荐 BGM 风格。"""
    return BGM_RECOMMENDATIONS.get(template, {"mood": "neutral", "bpm_range": (80, 120), "volume": 0.3})
