"""cut.jianying.viral_templates — 爆款短视频模板库。

基于全网爆款短视频结构调研：
- 黄金3秒钩子（前3秒决定72%用户去留）
- 中段价值填充
- 结尾CTA互动闭环

8 种爆款模板：tutorial / review / vlog / knowledge / drama / comparison / emotional / beat_sync
"""
from __future__ import annotations

import copy
from typing import Optional, Dict, Any, List, Union

from .draft import Draft, _new_id, _us, _hms
from . import materials, segments, text, effects, audio
from .pro_effects import apply_pro_transition
from .pro_text import add_huazi_text
from .pro_color import apply_color_preset


VIRAL_TEMPLATES = {
    "tutorial": {
        "name": "教程类", "name_en": "Tutorial",
        "structure": [
            {"phase": "hook", "duration_us": 3_000_000, "text_preset": "hook_red", "desc": "黄金3秒：抛出问题或痛点"},
            {"phase": "intro", "duration_us": 5_000_000, "text_preset": "chapter_title", "desc": "介绍：今天教你解决X"},
            {"phase": "demo_1", "duration_us": 8_000_000, "text_preset": "vlog_clean", "desc": "演示步骤1"},
            {"phase": "demo_2", "duration_us": 8_000_000, "text_preset": "vlog_clean", "desc": "演示步骤2"},
            {"phase": "demo_3", "duration_us": 8_000_000, "text_preset": "vlog_clean", "desc": "演示步骤3"},
            {"phase": "summary", "duration_us": 5_000_000, "text_preset": "tutorial_boxed", "desc": "总结要点"},
            {"phase": "cta", "duration_us": 3_000_000, "text_preset": "emphasis_red", "desc": "CTA：关注点赞收藏"},
        ],
        "transitions": ["flash_white", "smooth", "smooth", "smooth", "smooth", "flash_white"],
        "color_preset": "fresh",
    },
    "review": {
        "name": "测评类", "name_en": "Product Review",
        "structure": [
            {"phase": "hook", "duration_us": 3_000_000, "text_preset": "hook_yellow", "desc": "产品亮相 + 卖点钩子"},
            {"phase": "overview", "duration_us": 5_000_000, "text_preset": "chapter_title", "desc": "产品概览"},
            {"phase": "highlight_1", "duration_us": 6_000_000, "text_preset": "stat_number", "desc": "亮点1：数据展示"},
            {"phase": "highlight_2", "duration_us": 6_000_000, "text_preset": "stat_number", "desc": "亮点2：数据展示"},
            {"phase": "comparison", "duration_us": 8_000_000, "text_preset": "tutorial_boxed", "desc": "对比竞品"},
            {"phase": "verdict", "duration_us": 5_000_000, "text_preset": "emphasis_red", "desc": "购买建议"},
            {"phase": "cta", "duration_us": 3_000_000, "text_preset": "hook_red", "desc": "关注看更多测评"},
        ],
        "transitions": ["zoom_in", "smooth", "smooth", "smooth", "zoom_out", "flash_white"],
        "color_preset": "morandi",
    },
    "vlog": {
        "name": "vlog 日记", "name_en": "Vlog",
        "structure": [
            {"phase": "intro", "duration_us": 5_000_000, "text_preset": "chapter_title", "desc": "标题：我的一天"},
            {"phase": "morning", "duration_us": 8_000_000, "text_preset": "vlog_minimal", "desc": "早晨片段"},
            {"phase": "afternoon", "duration_us": 10_000_000, "text_preset": "vlog_minimal", "desc": "下午片段"},
            {"phase": "highlight", "duration_us": 8_000_000, "text_preset": "cinematic", "desc": "高光时刻"},
            {"phase": "evening", "duration_us": 8_000_000, "text_preset": "vlog_clean", "desc": "晚上片段"},
            {"phase": "reflection", "duration_us": 5_000_000, "text_preset": "quote_italic", "desc": "感悟"},
            {"phase": "outro", "duration_us": 3_000_000, "text_preset": "vlog_clean", "desc": "结尾"},
        ],
        "transitions": ["smooth", "smooth", "motion_blur", "smooth", "smooth", "fade"],
        "color_preset": "japanese_film",
    },
    "knowledge": {
        "name": "知识科普", "name_en": "Knowledge",
        "structure": [
            {"phase": "question", "duration_us": 4_000_000, "text_preset": "hook_red", "desc": "提问：你知道吗？"},
            {"phase": "context", "duration_us": 6_000_000, "text_preset": "vlog_clean", "desc": "背景知识"},
            {"phase": "explain", "duration_us": 10_000_000, "text_preset": "tutorial_boxed", "desc": "核心解释"},
            {"phase": "example", "duration_us": 8_000_000, "text_preset": "vlog_clean", "desc": "案例展示"},
            {"phase": "deeper", "duration_us": 6_000_000, "text_preset": "cinematic", "desc": "深度拓展"},
            {"phase": "summary", "duration_us": 4_000_000, "text_preset": "chapter_title", "desc": "总结升华"},
        ],
        "transitions": ["flash_white", "smooth", "smooth", "smooth", "zoom_in"],
        "color_preset": "teal_orange",
    },
    "drama": {
        "name": "剧情类", "name_en": "Drama",
        "structure": [
            {"phase": "conflict", "duration_us": 5_000_000, "text_preset": "cinematic", "desc": "冲突开场"},
            {"phase": "develop", "duration_us": 10_000_000, "text_preset": "vlog_minimal", "desc": "发展"},
            {"phase": "climax", "duration_us": 8_000_000, "text_preset": "emphasis_red", "desc": "高潮"},
            {"phase": "twist", "duration_us": 6_000_000, "text_preset": "hook_yellow", "desc": "反转"},
            {"phase": "ending", "duration_us": 5_000_000, "text_preset": "cinematic", "desc": "结局"},
        ],
        "transitions": ["flash_black", "smooth", "motion_blur", "flash_white"],
        "color_preset": "vintage_film",
    },
    "comparison": {
        "name": "测评对比", "name_en": "Comparison",
        "structure": [
            {"phase": "intro", "duration_us": 4_000_000, "text_preset": "hook_red", "desc": "A vs B 开场"},
            {"phase": "dim_1", "duration_us": 6_000_000, "text_preset": "stat_number", "desc": "维度1对比"},
            {"phase": "dim_2", "duration_us": 6_000_000, "text_preset": "stat_number", "desc": "维度2对比"},
            {"phase": "dim_3", "duration_us": 6_000_000, "text_preset": "stat_number", "desc": "维度3对比"},
            {"phase": "verdict", "duration_us": 5_000_000, "text_preset": "tutorial_boxed", "desc": "最终结论"},
            {"phase": "cta", "duration_us": 3_000_000, "text_preset": "emphasis_red", "desc": "关注看更多对比"},
        ],
        "transitions": ["zoom_in", "smooth", "smooth", "zoom_out", "flash_white"],
        "color_preset": "morandi",
    },
    "emotional": {
        "name": "情感类", "name_en": "Emotional",
        "structure": [
            {"phase": "scene", "duration_us": 6_000_000, "text_preset": "cinematic", "desc": "场景铺垫"},
            {"phase": "story", "duration_us": 12_000_000, "text_preset": "quote_italic", "desc": "故事讲述"},
            {"phase": "resonance", "duration_us": 8_000_000, "text_preset": "vlog_minimal", "desc": "共鸣点"},
            {"phase": "cta", "duration_us": 4_000_000, "text_preset": "vlog_clean", "desc": "互动引导"},
        ],
        "transitions": ["smooth", "smooth", "fade"],
        "color_preset": "japanese_film",
    },
    "beat_sync": {
        "name": "卡点类", "name_en": "Beat Sync",
        "structure": [
            {"phase": "build_up", "duration_us": 4_000_000, "text_preset": "vlog_minimal", "desc": "铺垫"},
            {"phase": "drop_1", "duration_us": 2_000_000, "text_preset": "emphasis_red", "desc": "卡点1"},
            {"phase": "drop_2", "duration_us": 2_000_000, "text_preset": "emphasis_red", "desc": "卡点2"},
            {"phase": "drop_3", "duration_us": 2_000_000, "text_preset": "emphasis_red", "desc": "卡点3"},
            {"phase": "drop_4", "duration_us": 2_000_000, "text_preset": "emphasis_red", "desc": "卡点4"},
            {"phase": "climax", "duration_us": 4_000_000, "text_preset": "hook_yellow", "desc": "高潮"},
            {"phase": "outro", "duration_us": 3_000_000, "text_preset": "vlog_minimal", "desc": "结尾"},
        ],
        "transitions": ["motion_blur", "zoom_in", "zoom_in", "zoom_in", "zoom_in", "flash_white"],
        "color_preset": "cyberpunk",
    },
}


def apply_viral_template(draft, template, video_material_ids,
                         bgm_material_id=None, texts=None,
                         auto_color=True, auto_transition=True):
    """应用爆款模板到 draft。"""
    if template not in VIRAL_TEMPLATES:
        raise KeyError(f"未知爆款模板: {template}. 可选: {list(VIRAL_TEMPLATES)}")

    cfg = VIRAL_TEMPLATES[template]
    structure = cfg["structure"]

    if len(video_material_ids) < len(structure):
        video_material_ids = (video_material_ids * (len(structure) // len(video_material_ids) + 1))[:len(structure)]

    vts = draft.video_tracks
    main_track_id = vts[0].id if vts else draft.add_track("video")
    tts = draft.text_tracks
    text_track_id = tts[0].id if tts else draft.add_track("text")

    cur_start = 0
    seg_ids = []
    text_ids = []
    for i, phase in enumerate(structure):
        mat_id = video_material_ids[i]
        mat = draft.find_material(mat_id)
        if not mat:
            continue
        seg_dur = phase["duration_us"]
        mat_dur = int(mat.get("duration", seg_dur))
        actual_dur = min(seg_dur, mat_dur) if mat_dur > 0 else seg_dur

        sid = materials.add_video_segment(draft, mat_id, track_id=main_track_id,
                                          start_us=cur_start, duration_us=actual_dur)
        seg_ids.append(sid)

        text_content = texts[i] if texts and i < len(texts) else phase["desc"]
        try:
            text_result = add_huazi_text(draft, text_content,
                                         start_us=cur_start + 200_000,
                                         duration_us=actual_dur - 400_000,
                                         preset=phase["text_preset"],
                                         track_id=text_track_id)
            text_ids.append(text_result["segment_id"])
        except Exception:
            pass

        cur_start += actual_dur

    transition_results = []
    if auto_transition:
        transitions = cfg.get("transitions", [])
        preset_map = {"fade": "smooth", "smooth": "smooth", "flash_white": "flash_white",
                      "flash_black": "flash_black", "zoom_in": "zoom_in",
                      "zoom_out": "zoom_out", "motion_blur": "motion_blur"}
        for i, trans_key in enumerate(transitions):
            if i + 1 >= len(seg_ids):
                break
            try:
                pro_preset = preset_map.get(trans_key, "smooth")
                r = apply_pro_transition(draft, seg_ids[i], seg_ids[i+1], preset=pro_preset)
                transition_results.append(r)
            except Exception:
                pass

    color_result = None
    if auto_color and cfg.get("color_preset"):
        try:
            applied = 0
            for sid in seg_ids:
                try:
                    apply_color_preset(draft, sid, cfg["color_preset"], intensity=0.8)
                    applied += 1
                except Exception:
                    pass
            color_result = {"applied": applied, "preset": cfg["color_preset"]}
        except Exception:
            pass

    bgm_result = None
    if bgm_material_id:
        try:
            ats = draft.audio_tracks
            audio_track_id = ats[0].id if ats else draft.add_track("audio")
            bgm_sid = materials.add_audio_segment(draft, bgm_material_id,
                                                  track_id=audio_track_id,
                                                  start_us=0, duration_us=cur_start, volume=0.3)
            bgm_result = {"segment_id": bgm_sid}
        except Exception:
            pass

    return {"template": template, "template_name": cfg["name"],
            "phases": len(structure), "segment_ids": seg_ids, "text_ids": text_ids,
            "transitions": len(transition_results), "color": color_result,
            "bgm": bgm_result, "total_duration_us": cur_start,
            "total_duration_hms": _hms(cur_start)}


def list_templates():
    """列出所有可用模板。"""
    return {k: {"name": v["name"], "name_en": v["name_en"],
                "phases": len(v["structure"]), "color": v.get("color_preset"),
                "transitions": v.get("transitions", [])}
            for k, v in VIRAL_TEMPLATES.items()}


def get_template_info(template):
    """获取模板详细信息。"""
    if template not in VIRAL_TEMPLATES:
        raise KeyError(f"未知模板: {template}")
    cfg = VIRAL_TEMPLATES[template]
    total = sum(p["duration_us"] for p in cfg["structure"])
    return {"template": template, "name": cfg["name"], "name_en": cfg["name_en"],
            "phases": cfg["structure"], "transitions": cfg.get("transitions", []),
            "color_preset": cfg.get("color_preset"), "total_duration_us": total,
            "total_duration_hms": _hms(total)}
