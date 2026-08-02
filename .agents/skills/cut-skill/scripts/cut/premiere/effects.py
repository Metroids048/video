"""cut.premiere.effects — 特效与转场。

通过 QE DOM 调用 Premiere 内置特效与转场。
特效/转场的查找通过名称匹配。
"""
from __future__ import annotations

from typing import Dict, Any, List

from .wrapper import get_app


def list_video_effects() -> List[str]:
    """列出所有可用视频特效名。"""
    app = get_app()
    app.enableQE()
    names = []
    try:
        qe_effects = app.qe.getVideoEffects()
        n = qe_effects.numItems if hasattr(qe_effects, "numItems") else 0
        for i in range(n):
            try:
                names.append(qe_effects[i].name)
            except Exception:
                continue
    except Exception:
        pass
    return names


def list_transitions() -> List[str]:
    """列出所有可用视频转场名。"""
    app = get_app()
    app.enableQE()
    names = []
    try:
        qe_trans = app.qe.getVideoTransitions()
        n = qe_trans.numItems if hasattr(qe_trans, "numItems") else 0
        for i in range(n):
            try:
                names.append(qe_trans[i].name)
            except Exception:
                continue
    except Exception:
        pass
    return names


def add_transition(track_index: int, clip_index: int,
                   transition_name: str = "Cross Dissolve",
                   duration_us: int = 500_000) -> Dict[str, Any]:
    """在 clip_index 与下一个 clip 之间加转场。

    transition_name 必须存在于 list_transitions() 返回值中。
    """
    app = get_app()
    app.enableQE()
    qe_proj = app.qe.project
    qe_seq = qe_proj.getActiveSequence()
    qe_track = qe_seq.getVideoTrackAt(track_index)
    qe_clips = qe_track.getCollections()
    if clip_index >= qe_clips.numItems - 1:
        raise IndexError("clip_index 后没有更多 clip")
    target_clip = qe_clips[clip_index]

    # 查找转场
    qe_trans = app.qe.getVideoTransitions()
    found = None
    for i in range(qe_trans.numItems):
        if qe_trans[i].name == transition_name:
            found = qe_trans[i]
            break
    if not found:
        return {"success": False, "error": f"未找到转场: {transition_name}"}

    # 应用：addTransition 在 Premiere QE DOM 中是 clip 的方法
    try:
        target_clip.addTransition(found, "", "", False, duration_us / 1_000_000)
        return {"success": True, "transition": transition_name, "duration_us": duration_us}
    except Exception as e:
        return {"success": False, "error": str(e)}


def add_video_effect(track_index: int, clip_index: int,
                     effect_name: str) -> Dict[str, Any]:
    """给 clip 应用视频特效。

    effect_name 例: "Black & White", "Gaussian Blur", "Lumetri Color"
    """
    app = get_app()
    app.enableQE()
    qe_proj = app.qe.project
    qe_seq = qe_proj.getActiveSequence()
    qe_track = qe_seq.getVideoTrackAt(track_index)
    qe_clips = qe_track.getCollections()
    if clip_index >= qe_clips.numItems:
        raise IndexError(f"clip_index {clip_index} 越界")
    target_clip = qe_clips[clip_index]

    # 查找特效
    qe_effects = app.qe.getVideoEffects()
    found = None
    for i in range(qe_effects.numItems):
        if qe_effects[i].name == effect_name:
            found = qe_effects[i]
            break
    if not found:
        return {"success": False, "error": f"未找到特效: {effect_name}"}

    try:
        target_clip.addVideoEffect(found)
        return {"success": True, "effect": effect_name}
    except Exception as e:
        return {"success": False, "error": str(e)}


def apply_lut(track_index: int, clip_index: int,
              lut_path: str, intensity: float = 1.0) -> Dict[str, Any]:
    """应用 .cube LUT 文件。

    实际是通过 Lumetri Color 的 Look 应用。
    """
    app = get_app()
    app.enableQE()
    qe_proj = app.qe.project
    qe_seq = qe_proj.getActiveSequence()
    qe_track = qe_seq.getVideoTrackAt(track_index)
    qe_clips = qe_track.getCollections()
    if clip_index >= qe_clips.numItems:
        raise IndexError(f"clip_index {clip_index} 越界")
    target_clip = qe_clips[clip_index]

    # 找 Lumetri Color 特效
    qe_effects = app.qe.getVideoEffects()
    lumetri = None
    for i in range(qe_effects.numItems):
        if "Lumetri" in qe_effects[i].name:
            lumetri = qe_effects[i]
            break
    if not lumetri:
        return {"success": False, "error": "未找到 Lumetri Color 特效"}

    try:
        target_clip.addVideoEffect(lumetri)
        # TODO: 设置 LUT path 与 intensity，需通过 effect 参数对象
        # 这里仅应用 Lumetri，LUT 设置需要进一步操作
        return {
            "success": True,
            "note": "Lumetri 已应用，请在 Premiere 中手动选择 LUT 文件",
            "lut_path": lut_path,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
