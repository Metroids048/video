"""cut.premiere.materials — 素材导入到 Premiere 项目面板。"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Dict, Any

from .wrapper import get_project, _ticks_to_us, _us_to_hms


def import_file(path: str, alias: Optional[str] = None,
                bin_name: Optional[str] = None) -> Dict[str, Any]:
    """导入单个文件到 Premiere 项目面板。

    返回 {project_item_id, name, media_path, duration_us, type}
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    proj = get_project()
    # 找目标 bin
    target_bin = proj.rootItem
    if bin_name:
        bins = proj.rootItem.findItems(bin_name, match_type=2) if hasattr(proj.rootItem, "findItems") else []
        if bins:
            target_bin = bins[0]
        else:
            # 创建 bin
            target_bin = proj.rootItem.createBin(bin_name)

    # pymiere 的 importFile 接收 {filepath, name, ...}
    proj.importFile(str(p.absolute()), name=alias, targetBin=target_bin)

    # 找到刚导入的 item
    items = proj.rootItem.findItems(p.stem, match_type=2) if hasattr(proj.rootItem, "findItems") else []
    if not items:
        # 回退：遍历所有 items
        items = list(proj.items)
        target_item = None
        for it in items:
            try:
                if it.getMediaPath() and str(p.absolute()) in it.getMediaPath():
                    target_item = it
                    break
            except Exception:
                continue
        if not target_item:
            return {"success": False, "error": "导入后未找到 item", "path": str(p)}
        items = [target_item]

    item = items[0]
    duration_us = 0
    try:
        if hasattr(item, "getMediaDuration"):
            duration_us = _ticks_to_us(item.getMediaDuration().ticks)
    except Exception:
        pass

    return {
        "success": True,
        "project_item_id": id(item),
        "name": alias or p.stem,
        "media_path": str(p.absolute()),
        "duration_us": duration_us,
        "duration_hms": _us_to_hms(duration_us),
    }


def import_files(paths: List[str], bin_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """批量导入。"""
    return [import_file(p, bin_name=bin_name) for p in paths]


def add_clip_to_timeline(project_item_id: int,
                         track_index: int = 0,
                         track_type: str = "video",
                         start_us: int = 0,
                         in_us: int = 0,
                         out_us: Optional[int] = None,
                         overwrite: bool = False) -> Dict[str, Any]:
    """把项目面板的 item 加到时间轴。

    project_item_id: import_file 返回的 id
    track_index: 轨道索引（0 = 最上层）
    track_type: "video" / "audio"
    start_us: 时间轴起点
    in_us/out_us: 素材内部入/出点
    overwrite: True 覆盖，False 插入
    """
    from .wrapper import get_active_sequence, _us_to_ticks
    seq = get_active_sequence()
    proj = get_project()

    # 找 project item
    item = None
    for it in proj.items:
        if id(it) == project_item_id:
            item = it
            break
    if not item:
        raise KeyError(f"project item {project_item_id} 不存在")

    # 选择轨道
    if track_type == "video":
        tracks = seq.videoTracks
    else:
        tracks = seq.audioTracks
    if track_index >= tracks.numItems:
        raise IndexError(f"track_index {track_index} 越界（共 {tracks.numItems} 条 {track_type} 轨）")
    track = tracks[track_index]

    # 设置 in/out
    if in_us or out_us:
        try:
            from pymiere.time import Time
            in_t = Time(ticks=_us_to_ticks(in_us))
            item.setInPoint(in_t)
            if out_us:
                out_t = Time(ticks=_us_to_ticks(out_us))
                item.setOutPoint(out_t)
        except Exception:
            pass

    # 插入或覆盖
    start_t_ticks = _us_to_ticks(start_us)
    if overwrite:
        track.overwriteClip(item, start_t_ticks)
    else:
        track.insertClip(item, start_t_ticks)

    return {"success": True, "track_index": track_index, "track_type": track_type, "start_us": start_us}


def list_project_items() -> List[Dict[str, Any]]:
    """列出项目面板所有素材。"""
    proj = get_project()
    out = []
    for it in proj.items:
        try:
            media_path = it.getMediaPath() if hasattr(it, "getMediaPath") else ""
            duration_us = 0
            if hasattr(it, "getMediaDuration"):
                duration_us = _ticks_to_us(it.getMediaDuration().ticks)
            out.append({
                "id": id(it),
                "name": it.name,
                "media_path": media_path,
                "duration_us": duration_us,
                "duration_hms": _us_to_hms(duration_us),
                "type": it.type if hasattr(it, "type") else "unknown",
            })
        except Exception as e:
            out.append({"error": str(e)})
    return out
