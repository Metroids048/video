"""cut.premiere.state — 反向读取 Premiere 当前项目状态。"""
from __future__ import annotations

from typing import Dict, Any, List

from .wrapper import (
    get_app, get_project, get_active_sequence,
    _ticks_to_us, _us_to_hms, _track_to_dict, _clip_to_dict,
    ensure_connected, HAS_PYMIERE,
)


def get_state() -> Dict[str, Any]:
    """读取 Premiere 当前项目状态。"""
    if not HAS_PYMIERE:
        return {"error": "pymiere 未安装", "backend": "premiere"}

    try:
        ensure_connected()
    except Exception as e:
        return {"error": str(e), "backend": "premiere"}

    try:
        app = get_app()
        proj = get_project()
        seq = get_active_sequence()
    except Exception as e:
        return {"error": str(e), "backend": "premiere"}

    # 序列信息
    try:
        seq_info = {
            "name": seq.name,
            "duration_us": _ticks_to_us(seq.end.ticks),
            "duration_hms": _us_to_hms(_ticks_to_us(seq.end.ticks)),
            "video_tracks_count": seq.videoTracks.numItems,
            "audio_tracks_count": seq.audioTracks.numItems,
            "frame_size": {
                "width": getattr(seq.frameSizeHorizontal, "ticks", 0) if hasattr(seq, "frameSizeHorizontal") else 0,
                "height": getattr(seq.frameSizeVertical, "ticks", 0) if hasattr(seq, "frameSizeVertical") else 0,
            } if False else {"width": 0, "height": 0},  # pymiere 帧尺寸 API 不稳定
        }
    except Exception as e:
        seq_info = {"error": str(e)}

    # 项目信息
    try:
        proj_info = {
            "name": proj.name,
            "path": proj.path if hasattr(proj, "path") else "",
        }
    except Exception:
        proj_info = {}

    return {
        "backend": "premiere",
        "app_version": getattr(app, "version", "?"),
        "project": proj_info,
        "active_sequence": seq_info,
        "platform_info": {"running": True},
    }


def list_materials() -> List[Dict[str, Any]]:
    """列出项目面板所有素材。"""
    from .materials import list_project_items
    return list_project_items()


def get_timeline() -> Dict[str, Any]:
    """读取当前序列的完整轨道与 clip 结构。"""
    seq = get_active_sequence()

    video_tracks = []
    for i in range(seq.videoTracks.numItems):
        video_tracks.append(_track_to_dict(seq.videoTracks[i], "video"))

    audio_tracks = []
    for i in range(seq.audioTracks.numItems):
        audio_tracks.append(_track_to_dict(seq.audioTracks[i], "audio"))

    duration_us = _ticks_to_us(seq.end.ticks)
    return {
        "backend": "premiere",
        "sequence_name": seq.name,
        "duration_us": duration_us,
        "duration_hms": _us_to_hms(duration_us),
        "video_tracks": video_tracks,
        "audio_tracks": audio_tracks,
        "tracks": video_tracks + audio_tracks,
    }


def get_selection() -> Dict[str, Any]:
    """读取当前选中的 clip。"""
    seq = get_active_sequence()
    selected = []
    for tt, tracks in (("video", seq.videoTracks), ("audio", seq.audioTracks)):
        for i in range(tracks.numItems):
            track = tracks[i]
            for j in range(track.clips.numItems):
                clip = track.clips[j]
                try:
                    if clip.isSelected():
                        selected.append(_clip_to_dict(clip, id(track), tt))
                except Exception:
                    continue
    return {"selected_clips": selected, "count": len(selected)}


if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--timeline":
        print(json.dumps(get_timeline(), indent=2, ensure_ascii=False, default=str))
    elif len(sys.argv) > 1 and sys.argv[1] == "--materials":
        print(json.dumps(list_materials(), indent=2, ensure_ascii=False, default=str))
    else:
        print(json.dumps(get_state(), indent=2, ensure_ascii=False, default=str))
