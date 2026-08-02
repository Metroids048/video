"""cut.premiere.audio — 音频混音。"""
from __future__ import annotations

from typing import Dict, Any

from .wrapper import get_app


def set_volume(track_index: int, clip_index: int,
               volume_db: float) -> Dict[str, Any]:
    """设置 clip 音量（分贝）。

    0 dB = 原音量，-6 dB = 一半，+6 dB = 双倍。
    Premiere 用 dB 单位，与剪映的 0-1 不同。
    """
    app = get_app()
    app.enableQE()
    qe_proj = app.qe.project
    qe_seq = qe_proj.getActiveSequence()
    qe_track = qe_seq.getAudioTrackAt(track_index)
    qe_clips = qe_track.getCollections()
    if clip_index >= qe_clips.numItems:
        raise IndexError(f"clip_index {clip_index} 越界")
    target_clip = qe_clips[clip_index]

    try:
        components = target_clip.getComponents()
        vol_comp = None
        for i in range(components.numItems):
            comp = components[i]
            if "Volume" in comp.name or "音量" in comp.name:
                vol_comp = comp
                break

        # 若无 Volume 组件，添加一次（避免无限递归）
        if vol_comp is None:
            vol_effect = app.qe.getAudioEffectByName("Volume")
            if vol_effect is None:
                return {"success": False, "error": "未找到 Volume 音频特效"}
            target_clip.addComponent(vol_effect)
            # 重新获取组件
            components = target_clip.getComponents()
            for i in range(components.numItems):
                comp = components[i]
                if "Volume" in comp.name or "音量" in comp.name:
                    vol_comp = comp
                    break

        if vol_comp is None:
            return {"success": False, "error": "Volume 组件添加失败"}

        # 设置 volume 参数
        props = vol_comp.getProperties() if hasattr(vol_comp, "getProperties") else None
        if props:
            for j in range(props.numItems if hasattr(props, "numItems") else 0):
                prop = props[j]
                if "level" in prop.name.lower() or "volume" in prop.name.lower():
                    prop.setValue(volume_db, True)
                    return {"success": True, "volume_db": volume_db}
        return {"success": False, "error": "未找到 volume/level 参数"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def add_fade_in(track_index: int, clip_index: int,
                duration_us: int = 500_000) -> Dict[str, Any]:
    """音频淡入。

    通过 Premiere 的音频轨道关键帧实现：clip 起始处音量 = -Infinity（实际用极小值），
    duration_us 后回到原音量。

    注意：pymiere 对关键帧 API 支持有限，本实现尝试通过 Volume 组件的 level 参数
    设置两个关键帧。如失败则返回 success=False，建议用户在 Premiere UI 手动加。
    """
    app = get_app()
    app.enableQE()
    qe_proj = app.qe.project
    qe_seq = qe_proj.getActiveSequence()
    qe_track = qe_seq.getAudioTrackAt(track_index)
    qe_clips = qe_track.getCollections()
    if clip_index >= qe_clips.numItems:
        raise IndexError(f"clip_index {clip_index} 越界")
    target_clip = qe_clips[clip_index]

    try:
        from .wrapper import _ticks_to_us
        clip_start_us = _ticks_to_us(int(target_clip.start.ticks))
        fade_end_us = clip_start_us + duration_us

        # 尝试通过组件关键帧 API
        components = target_clip.getComponents()
        vol_comp = None
        for i in range(components.numItems):
            comp = components[i]
            if "Volume" in comp.name or "音量" in comp.name:
                vol_comp = comp
                break

        if vol_comp is None:
            # 添加 Volume 组件
            vol_effect = app.qe.getAudioEffectByName("Volume")
            if vol_effect is None:
                return {"success": False, "error": "未找到 Volume 音频特效，无法创建关键帧"}
            target_clip.addComponent(vol_effect)
            # 重新获取
            components = target_clip.getComponents()
            for i in range(components.numItems):
                if "Volume" in components[i].name or "音量" in components[i].name:
                    vol_comp = components[i]
                    break

        if vol_comp is None:
            return {"success": False, "error": "Volume 组件添加失败"}

        # 尝试设置关键帧（API 因 Premiere 版本而异，这里做防御性尝试）
        props = vol_comp.getProperties() if hasattr(vol_comp, "getProperties") else None
        if props:
            for j in range(props.numItems if hasattr(props, "numItems") else 0):
                prop = props[j]
                if hasattr(prop, "addKeyframe"):
                    # 起始处音量极低
                    prop.addKeyframeAtTime(clip_start_us / 1_000_000, -96.0)
                    # duration 后回到 0 dB
                    prop.addKeyframeAtTime(fade_end_us / 1_000_000, 0.0)
                    return {"success": True, "fade_in_us": duration_us}

        return {
            "success": False,
            "error": "Premiere 版本不支持关键帧 API，请在 UI 中手动添加淡入",
            "hint": "选择 clip → 效果控件 → 音量 → 电平 → 创建关键帧",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def add_fade_out(track_index: int, clip_index: int,
                 duration_us: int = 500_000) -> Dict[str, Any]:
    """音频淡出。clip 末尾处音量渐变到极低。"""
    app = get_app()
    app.enableQE()
    qe_proj = app.qe.project
    qe_seq = qe_proj.getActiveSequence()
    qe_track = qe_seq.getAudioTrackAt(track_index)
    qe_clips = qe_track.getCollections()
    if clip_index >= qe_clips.numItems:
        raise IndexError(f"clip_index {clip_index} 越界")
    target_clip = qe_clips[clip_index]

    try:
        from .wrapper import _ticks_to_us
        clip_end_us = _ticks_to_us(int(target_clip.end.ticks))
        fade_start_us = clip_end_us - duration_us

        components = target_clip.getComponents()
        vol_comp = None
        for i in range(components.numItems):
            comp = components[i]
            if "Volume" in comp.name or "音量" in comp.name:
                vol_comp = comp
                break

        if vol_comp is None:
            vol_effect = app.qe.getAudioEffectByName("Volume")
            if vol_effect is None:
                return {"success": False, "error": "未找到 Volume 音频特效"}
            target_clip.addComponent(vol_effect)
            components = target_clip.getComponents()
            for i in range(components.numItems):
                if "Volume" in components[i].name or "音量" in components[i].name:
                    vol_comp = components[i]
                    break

        if vol_comp is None:
            return {"success": False, "error": "Volume 组件添加失败"}

        props = vol_comp.getProperties() if hasattr(vol_comp, "getProperties") else None
        if props:
            for j in range(props.numItems if hasattr(props, "numItems") else 0):
                prop = props[j]
                if hasattr(prop, "addKeyframe"):
                    prop.addKeyframeAtTime(fade_start_us / 1_000_000, 0.0)
                    prop.addKeyframeAtTime(clip_end_us / 1_000_000, -96.0)
                    return {"success": True, "fade_out_us": duration_us}

        return {
            "success": False,
            "error": "Premiere 版本不支持关键帧 API，请在 UI 中手动添加淡出",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def apply_audio_effect(track_index: int, clip_index: int,
                       effect_name: str) -> Dict[str, Any]:
    """应用音频特效。

    常用 effect_name: "DeNoise", "Reverb", "Parametric Equalizer",
    "Dynamics", "Stereo Widener", "Bass"
    """
    app = get_app()
    app.enableQE()
    qe_proj = app.qe.project
    qe_seq = qe_proj.getActiveSequence()
    qe_track = qe_seq.getAudioTrackAt(track_index)
    qe_clips = qe_track.getCollections()
    if clip_index >= qe_clips.numItems:
        raise IndexError(f"clip_index {clip_index} 越界")
    target_clip = qe_clips[clip_index]

    qe_audio_effects = app.qe.getAudioEffects()
    found = None
    for i in range(qe_audio_effects.numItems):
        if qe_audio_effects[i].name == effect_name:
            found = qe_audio_effects[i]
            break
    if not found:
        return {"success": False, "error": f"未找到音频特效: {effect_name}"}

    try:
        target_clip.addComponent(found)
        return {"success": True, "effect": effect_name}
    except Exception as e:
        return {"success": False, "error": str(e)}
