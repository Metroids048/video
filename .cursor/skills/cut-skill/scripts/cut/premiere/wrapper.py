"""cut.premiere.wrapper — pymiere 连接与基础封装。

pymiere 通过 ExtendScript 桥接 Premiere Pro。
要求：
- Premiere Pro 已运行
- 已打开一个项目
- pymiere 已安装 (pip install pymiere)

pymiere 对象层级：
    pymiere.objects.app                → App
        .project                       → Project
            .items                     → 项目面板素材集合
            .activeSequence             → 当前活动序列
                .videoTracks            → 视频轨道集合
                .audioTracks            → 音频轨道集合
                    .clips              → 片段集合
                    .insertClip()
                    .overwriteClip()

首次调用会有 2-3 秒延迟（CEP WebSocket 建立连接）。
"""
from __future__ import annotations

import time
from typing import Any, Dict, Union

try:
    import pymiere
    from pymiere import objects as _pobj
    HAS_PYMIERE = True
except ImportError:
    HAS_PYMIERE = False
    pymiere = None
    _pobj = None


class PremiereError(Exception):
    pass


class PremiereNotRunningError(PremiereError):
    pass


# ---------------------------------------------------------------------------
# 连接管理
# ---------------------------------------------------------------------------

def ensure_connected(timeout: float = 10.0) -> None:
    """确保 pymiere 与 Premiere 已建立连接。

    首次调用会触发 CEP WebSocket 连接，可能慢。
    """
    if not HAS_PYMIERE:
        raise PremiereError(
            "pymiere 未安装。请运行: pip install pymiere\n"
            "如果安装失败，请确认 Python 版本 ≥ 3.9 且 Premiere 已运行。"
        )
    start = time.time()
    last_err = None
    while time.time() - start < timeout:
        try:
            app = _pobj.app
            # 触发一次实际调用验证连接
            _ = app.version
            return
        except Exception as e:
            last_err = e
            time.sleep(0.5)
    raise PremiereNotRunningError(
        f"无法连接 Premiere Pro: {last_err}\n"
        "请确认：\n"
        "1. Premiere Pro 已启动\n"
        "2. 已打开一个项目\n"
        "3. 首选项 → 脚本 → 已启用脚本调试\n"
        "4. 安装的 pymiere 版本与 Premiere 兼容"
    )


def get_app():
    """返回 pymiere 的 app 对象。"""
    ensure_connected()
    return _pobj.app


def get_project():
    """返回当前 project。"""
    app = get_app()
    if not app.project:
        raise PremiereError("Premiere 中没有打开的项目。请先创建或打开一个项目。")
    return app.project


def get_active_sequence():
    """返回当前活动序列。"""
    proj = get_project()
    if not proj.activeSequence:
        raise PremiereError("当前项目没有活动序列。请在 Premiere 中打开或创建一个序列。")
    return proj.activeSequence


# ---------------------------------------------------------------------------
# 通用工具
# ---------------------------------------------------------------------------

def _ticks_to_us(ticks: int) -> int:
    """Premiere 用 ticks 表示时间（254016000000 ticks = 1 秒）。转微秒。"""
    if not ticks:
        return 0
    return int(int(ticks) / 254016000000 * 1_000_000)


def _us_to_ticks(us: int) -> int:
    """微秒转 ticks。"""
    return int(us / 1_000_000 * 254016000000)


def _s_to_ticks(s: float) -> int:
    return int(s * 254016000000)


def _time_to_us(t: Union[int, float, str], unit: str = "us") -> int:
    """统一时间格式转微秒。"""
    if isinstance(t, str):
        parts = t.strip().split(":")
        if len(parts) == 3:
            h, m, s = parts
            return int(float(h) * 3_600_000_000 + float(m) * 60_000_000 + float(s) * 1_000_000)
        elif len(parts) == 2:
            m, s = parts
            return int(float(m) * 60_000_000 + float(s) * 1_000_000)
        else:
            return int(float(parts[0]) * 1_000_000)
    v = float(t)
    if unit == "us":
        return int(v)
    if unit == "ms":
        return int(v * 1000)
    if unit == "s":
        return int(v * 1_000_000)
    raise ValueError(f"unknown unit {unit}")


def _us_to_hms(us: int) -> str:
    if us is None:
        return "00:00:00.000"
    total_ms = us // 1000
    h = total_ms // 3_600_000
    m = (total_ms % 3_600_000) // 60_000
    s = (total_ms % 60_000) // 1000
    ms = total_ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _clip_to_dict(clip, track_id: str, track_type: str) -> Dict[str, Any]:
    """把 pymiere Clip 对象转成 dict。"""
    try:
        start_us = _ticks_to_us(clip.start.ticks)
        end_us = _ticks_to_us(clip.end.ticks)
        in_us = _ticks_to_us(clip.inPoint.ticks)
        out_us = _ticks_to_us(clip.outPoint.ticks)
    except Exception:
        start_us = end_us = in_us = out_us = 0

    name = ""
    try:
        name = clip.name
    except Exception:
        pass

    media_path = ""
    try:
        if clip.projectItem and clip.projectItem.getMediaPath():
            media_path = clip.projectItem.getMediaPath()
    except Exception:
        pass

    return {
        "id": id(clip),  # pymiere Clip 没有 id 字段，用 Python id 作占位
        "name": name,
        "track_id": track_id,
        "track_type": track_type,
        "start_us": start_us,
        "end_us": end_us,
        "duration_us": end_us - start_us,
        "start_hms": _us_to_hms(start_us),
        "end_hms": _us_to_hms(end_us),
        "in_us": in_us,
        "out_us": out_us,
        "media_path": media_path,
    }


def _track_to_dict(track, track_type: str) -> Dict[str, Any]:
    """把 pymiere Track 对象转成 dict。"""
    clips_out = []
    try:
        clips = track.clips
        for i in range(clips.numItems):
            clips_out.append(_clip_to_dict(clips[i], id(track), track_type))
    except Exception:
        pass
    return {
        "id": id(track),
        "type": track_type,
        "name": getattr(track, "name", "") or "",
        "segments_count": len(clips_out),
        "clips": clips_out,
    }
