"""cut.jianying.audio — 音频混音操作。

剪映音频相关字段：
- segment.volume: 整段音量（0-1+）
- segment.common_keyframes: 关键帧，可做音量自动化
- materials.audio_effects: 降噪/混响等效果

本模块提供：
- set_volume
- add_audio_fade_in / add_audio_fade_out
- apply_audio_ducking（背景音自动避让）
- apply_audio_effect（降噪/混响等）
"""
from __future__ import annotations


from .draft import Draft, _new_id
from .effects import add_keyframe


def set_volume(draft: Draft, segment_id: str, volume: float) -> None:
    """设置片段音量。

    volume: 0.0 = 静音，1.0 = 原音量，2.0 = 放大一倍
    剪映支持 0-10，超过 1 视为增益。
    """
    raw = draft.get_segment_raw(segment_id)
    if not raw:
        raise KeyError(f"segment {segment_id} 不存在")
    raw["volume"] = float(volume)
    draft._modified = True


def add_audio_fade_in(draft: Draft, segment_id: str,
                      duration_us: int = 500_000) -> None:
    """音频淡入（音量 0→原值）。"""
    raw = draft.get_segment_raw(segment_id)
    if not raw:
        raise KeyError(segment_id)
    start = raw.get("target_timerange", {}).get("start", 0)
    target_vol = raw.get("volume", 1.0)
    add_keyframe(draft, segment_id, start, 0.0, field="volume")
    add_keyframe(draft, segment_id, start + duration_us, target_vol, field="volume")


def add_audio_fade_out(draft: Draft, segment_id: str,
                       duration_us: int = 500_000) -> None:
    """音频淡出。"""
    raw = draft.get_segment_raw(segment_id)
    if not raw:
        raise KeyError(segment_id)
    tt = raw.get("target_timerange", {})
    end = tt.get("start", 0) + tt.get("duration", 0)
    target_vol = raw.get("volume", 1.0)
    add_keyframe(draft, segment_id, end - duration_us, target_vol, field="volume")
    add_keyframe(draft, segment_id, end, 0.0, field="volume")


# 音频效果 preset
AUDIO_EFFECT_PRESETS = {
    "denoise": "audio_effect.denoise",       # 降噪
    "denoise_strong": "audio_effect.denoise_strong",
    "reverb_room": "audio_effect.reverb_room",
    "reverb_hall": "audio_effect.reverb_hall",
    "reverb_church": "audio_effect.reverb_church",
    "pitch_up": "audio_effect.pitch_up",
    "pitch_down": "audio_effect.pitch_down",
    "compressor": "audio_effect.compressor",
    "equalizer": "audio_effect.equalizer",
    "vocal_remove": "audio_effect.vocal_remove",   # 人声消除
    "deess": "audio_effect.deess",
}


def apply_audio_effect(draft: Draft, segment_id: str,
                       preset: str = "denoise",
                       intensity: float = 1.0) -> str:
    """给音频 segment 应用音频效果。"""
    if preset not in AUDIO_EFFECT_PRESETS:
        raise KeyError(f"未知音频效果: {preset}")

    raw = draft.get_segment_raw(segment_id)
    if not raw:
        raise KeyError(segment_id)

    fx_id = _new_id()
    fx = {
        "id": fx_id,
        "type": "audio_effect",
        "resource_id": AUDIO_EFFECT_PRESETS[preset],
        "name": preset,
        "intensity": intensity,
        "is_valid": True,
    }
    draft.add_material("audio_effect", fx)

    refs = raw.setdefault("extra_material_refs", [])
    refs.append(fx_id)
    draft._modified = True
    return fx_id


def apply_ducking(draft: Draft,
                  voice_segment_ids: list,
                  bgm_segment_id: str,
                  duck_level: float = 0.3,
                  fade_us: int = 200_000) -> None:
    """背景音自动避让人声。

    在 voice_segment 出现时把 bgm 音量降到 duck_level，
    voice 结束后 fade 回原值。

    实现：遍历 voice segments 的时间范围，给 bgm 加对应区间的音量关键帧。
    """
    bgm_raw = draft.get_segment_raw(bgm_segment_id)
    if not bgm_raw:
        raise KeyError(f"bgm segment {bgm_segment_id} 不存在")
    bgm_vol = bgm_raw.get("volume", 1.0)

    # 收集 voice 时间范围
    voice_ranges = []
    for sid in voice_segment_ids:
        s = draft.get_segment_raw(sid)
        if not s:
            continue
        tt = s.get("target_timerange", {})
        voice_ranges.append((tt.get("start", 0), tt.get("start", 0) + tt.get("duration", 0)))
    voice_ranges.sort()

    if not voice_ranges:
        return

    # 在 bgm 上加关键帧
    cur = bgm_raw.get("target_timerange", {}).get("start", 0)
    # 起始处先加一个原音量关键帧，确保开头音量正确
    add_keyframe(draft, bgm_segment_id, cur, bgm_vol, field="volume")

    for vstart, vend in voice_ranges:
        # voice 前 fade 到 duck_level
        if vstart - fade_us > cur:
            add_keyframe(draft, bgm_segment_id, vstart - fade_us, bgm_vol, field="volume")
        add_keyframe(draft, bgm_segment_id, vstart, bgm_vol * duck_level, field="volume")
        # voice 后 fade 回 bgm_vol
        add_keyframe(draft, bgm_segment_id, vend, bgm_vol * duck_level, field="volume")
        add_keyframe(draft, bgm_segment_id, vend + fade_us, bgm_vol, field="volume")
        cur = vend + fade_us
