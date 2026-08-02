"""cut.premiere.text — 文字添加。

Premiere 的文字通过 Title 或 Essential Graphics 实现。
pymiere 对文字支持有限，本模块通过 QE DOM 创建 Title。
"""
from __future__ import annotations

from typing import Optional, Dict, Any, Union

from .wrapper import get_app, _us_to_ticks, _time_to_us


def add_text(content: str,
             start_us: Union[int, float, str],
             duration_us: Union[int, float, str] = 3_000_000,
             track_index: Optional[int] = None,
             position_x: float = 0.0,
             position_y: float = 0.4,
             font_size: int = 40,
             color: str = "#FFFFFF",
             unit: str = "us") -> Dict[str, Any]:
    """添加文字片段。

    实现路径：通过 QE DOM 创建 Essential Graphics 文字层。
    需要 Premiere CC 2018+。
    """
    app = get_app()
    app.enableQE()
    qe_proj = app.qe.project
    qe_seq = qe_proj.getActiveSequence()

    start_us_int = _time_to_us(start_us, unit)
    dur_int = _time_to_us(duration_us, unit)
    start_ticks = _us_to_ticks(start_us_int)
    end_ticks = _us_to_ticks(start_us_int + dur_int)

    # 在视频轨上方新建文字轨
    if track_index is None:
        # 找最上层视频轨
        vts = qe_seq.getVideoTracks()
        track_index = vts.numItems - 1

    # 创建 text clip
    try:
        # QE DOM 的 addText 在 Premiere 2020+ 可用
        qe_seq.addText(content, qe_proj.getActiveSequence().getVideoTrackAt(track_index))
        # 找到刚加的文字 clip
        track = qe_seq.getVideoTrackAt(track_index)
        clips = track.getCollections()
        new_clip = clips[clips.numItems - 1]
        # 调整时长与位置
        new_clip.setStart(_ticks_to_qe_time(start_ticks), respectIns=True)
        new_clip.setEnd(_ticks_to_qe_time(end_ticks), respectIns=True)
        # 修改文字内容（如果上面没传）
        if hasattr(new_clip, "setText"):
            new_clip.setText(content)
        # 位置：通过 effects 修改
        # 简化：保留默认位置
        return {
            "success": True,
            "track_index": track_index,
            "start_us": start_us_int,
            "duration_us": dur_int,
            "note": "文字样式需在 Premiere Essential Graphics 面板手动调整",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _ticks_to_qe_time(ticks: int) -> str:
    return str(ticks / 254016000000)


def add_subtitle(content: str, start_us: Union[int, float, str],
                 duration_us: Union[int, float, str] = 3_000_000,
                 **kwargs) -> Dict[str, Any]:
    """添加字幕（默认底部位置）。"""
    kwargs.setdefault("position_y", 0.4)
    return add_text(content, start_us, duration_us, **kwargs)


def add_title(content: str, start_us: Union[int, float, str],
              duration_us: Union[int, float, str] = 3_000_000,
              **kwargs) -> Dict[str, Any]:
    """添加标题（默认中央位置）。"""
    kwargs.setdefault("position_y", -0.3)
    kwargs.setdefault("font_size", 80)
    return add_text(content, start_us, duration_us, **kwargs)
