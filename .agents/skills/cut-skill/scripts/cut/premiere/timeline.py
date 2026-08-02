"""cut.premiere.timeline — 时间轴裁切操作。"""
from __future__ import annotations

from typing import Optional, Union, Dict, Any

from .wrapper import (
    get_active_sequence, _us_to_ticks, _time_to_us
)


def split_clip(track_index: int, track_type: str, clip_index: int,
               at_us: Union[int, float, str], unit: str = "us") -> Dict[str, Any]:
    """在第 clip_index 个 clip 的 at_us 处切分。

    at_us 是时间轴绝对坐标。
    """
    seq = get_active_sequence()
    tracks = seq.videoTracks if track_type == "video" else seq.audioTracks
    if track_index >= tracks.numItems:
        raise IndexError(f"track_index {track_index} 越界")
    track = tracks[track_index]
    if clip_index >= track.clips.numItems:
        raise IndexError(f"clip_index {clip_index} 越界（共 {track.clips.numItems} 个 clip）")

    at_ticks = _us_to_ticks(_time_to_us(at_us, unit))
    # pymiere 的 addClipsAtPlayhead 或 razor
    # 实际上 Premiere 的切分是 razor 工具
    # pymiere 提供: track.clips[i].start/end 是只读，切分用 seq.razor()
    try:
        seq.razor(at_ticks)  # 在所有轨道该时间点切分
    except AttributeError:
        # 旧版本没有 razor，用 QE DOM
        from .wrapper import get_app
        get_app().enableQE()
        qe_proj = get_app().qe.project
        qe_seq = qe_proj.getActiveSequence()
        qe_seq.razor(_ticks_to_qe_time(at_ticks))

    return {"success": True, "track_index": track_index, "at_us": _time_to_us(at_us, unit)}


def _ticks_to_qe_time(ticks: int) -> str:
    """QE DOM 用秒数字符串表示时间。"""
    s = ticks / 254016000000
    return str(s)


def trim_clip(track_index: int, track_type: str, clip_index: int,
              new_start_us: Optional[Union[int, float, str]] = None,
              new_end_us: Optional[Union[int, float, str]] = None,
              unit: str = "us") -> Dict[str, Any]:
    """调整 clip 的入点/出点。

    new_start_us / new_end_us 是时间轴绝对坐标。
    """
    seq = get_active_sequence()
    tracks = seq.videoTracks if track_type == "video" else seq.audioTracks
    if track_index >= tracks.numItems:
        raise IndexError(f"track_index {track_index} 越界")
    track = tracks[track_index]
    if clip_index >= track.clips.numItems:
        raise IndexError(f"clip_index {clip_index} 越界")
    track.clips[clip_index]

    # pymiere 的 clip.start/end 是 Time 对象，可写
    # 但实际修改需要走 QE DOM 或 movePlayhead + razor + remove
    # 这里用 QE DOM 的 setInPoint/setOutPoint
    from .wrapper import get_app
    get_app().enableQE()
    qe_proj = get_app().qe.project
    qe_seq = qe_proj.getActiveSequence()
    qe_tracks = qe_seq.getVideoTracks() if track_type == "video" else qe_seq.getAudioTracks()
    qe_track = qe_tracks[track_index]
    qe_clips = qe_track.getCollections()
    qe_clip = qe_clips[clip_index]

    if new_start_us is not None:
        ns_ticks = _us_to_ticks(_time_to_us(new_start_us, unit))
        qe_clip.setInPoint(_ticks_to_qe_time(ns_ticks), respectIns=True) if hasattr(qe_clip, "setInPoint") else None

    if new_end_us is not None:
        ne_ticks = _us_to_ticks(_time_to_us(new_end_us, unit))
        qe_clip.setOutPoint(_ticks_to_qe_time(ne_ticks), respectIns=True) if hasattr(qe_clip, "setOutPoint") else None

    return {"success": True}


def remove_clip(track_index: int, track_type: str, clip_index: int,
                ripple: bool = True) -> Dict[str, Any]:
    """删除 clip。

    ripple=True 时把后面的 clip 前移填补空隙。
    """
    seq = get_active_sequence()
    tracks = seq.videoTracks if track_type == "video" else seq.audioTracks
    track = tracks[track_index]
    clip = track.clips[clip_index]

    # 选中并删除
    try:
        # pymiere 没有直接 remove 接口，通过选中 + 删除键
        clip.setSelected(True, inFrame=0, outFrame=0)
        from .wrapper import get_app
        get_app().project.activeSequence.setInPoint(clip.start.ticks)
        get_app().project.activeSequence.setOutPoint(clip.end.ticks)

        if ripple:
            # ripple delete
            qe_proj = get_app().qe.project
            qe_seq = qe_proj.getActiveSequence()
            qe_seq.performRippleDelete(_ticks_to_qe_time(int(clip.start.ticks)),
                                        _ticks_to_qe_time(int(clip.end.ticks)))
        else:
            # 普通删除（lifter）
            qe_proj = get_app().qe.project
            qe_seq = qe_proj.getActiveSequence()
            qe_seq.performLift(_ticks_to_qe_time(int(clip.start.ticks)),
                                _ticks_to_qe_time(int(clip.end.ticks)))
    except Exception as e:
        return {"success": False, "error": str(e)}

    return {"success": True}


def move_clip(track_index: int, track_type: str, clip_index: int,
              new_start_us: Union[int, float, str],
              new_track_index: Optional[int] = None,
              unit: str = "us") -> Dict[str, Any]:
    """移动 clip。"""
    seq = get_active_sequence()
    tracks = seq.videoTracks if track_type == "video" else seq.audioTracks
    track = tracks[track_index]
    track.clips[clip_index]

    # 简化实现：通过 QE DOM 的 move
    # 实际上 Premiere 中移动 clip 用 setStart / setEnd
    try:
        from .wrapper import get_app
        get_app().enableQE()
        qe_proj = get_app().qe.project
        qe_seq = qe_proj.getActiveSequence()
        qe_tracks = qe_seq.getVideoTracks() if track_type == "video" else qe_seq.getAudioTracks()
        qe_track = qe_tracks[track_index]
        qe_clips = qe_track.getCollections()
        qe_clip = qe_clips[clip_index]
        ns_ticks = _us_to_ticks(_time_to_us(new_start_us, unit))
        qe_clip.setStart(_ticks_to_qe_time(ns_ticks), respectIns=True) if hasattr(qe_clip, "setStart") else None
    except Exception as e:
        return {"success": False, "error": str(e)}

    return {"success": True}
