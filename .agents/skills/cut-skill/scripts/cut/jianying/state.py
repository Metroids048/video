"""cut.jianying.state — 上下文感知与反向读取。

让 agent 能够"看到"剪映当前项目里有什么：素材池、轨道、片段、选中元素。
所有方法都是只读的，不会修改 draft。
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional

from .draft import Draft, _hms
from .. import platform as P


def get_state(project_name: Optional[str] = None,
              project_dir: Optional[str] = None,
              app: str = "jianying") -> Dict[str, Any]:
    """读取剪映项目状态。

    自动找最近修改的项目（如果未指定 name/dir）。
    """
    if not project_name and not project_dir:
        drafts = P.list_drafts(app=app)
        if not drafts:
            return {"error": "未找到任何剪映项目", "backend": "jianying"}
        project_name = drafts[0]["name"]

    draft = Draft.open(project_name=project_name, project_dir=project_dir, app=app)
    return _draft_to_state(draft)


def _draft_to_state(draft: Draft) -> Dict[str, Any]:
    """把 Draft 转成 agent 友好的状态摘要。"""
    summary = draft.to_summary()
    return {
        "backend": "jianying",
        "platform": P._os_name(),
        "app_version": draft.schema_version,
        "project_path": str(draft.project_dir),
        "project_name": draft.name,
        "duration_us": draft.duration,
        "duration_hms": draft.duration_hms,
        "canvas": draft.canvas,
        "tracks": summary["tracks"],
        "materials": summary["materials"],
        "selection": None,  # 剪映 draft 不记录选中状态
    }


def list_materials(project_name: Optional[str] = None,
                   project_dir: Optional[str] = None,
                   mtype: Optional[str] = None,
                   app: str = "jianying") -> List[Dict[str, Any]]:
    """列出素材池。mtype 可选 video/audio/image/sticker/text/effect。"""
    draft = _open_or_recent(project_name, project_dir, app)
    out = []
    for m in draft.list_materials(mtype=mtype):
        out.append({
            "id": m.id,
            "type": m.type,
            "path": m.path,
            "duration_us": m.duration,
            "duration_hms": _hms(m.duration),
            "width": m.width,
            "height": m.height,
        })
    return out


def get_timeline(project_name: Optional[str] = None,
                 project_dir: Optional[str] = None,
                 app: str = "jianying") -> Dict[str, Any]:
    """读取完整时间轴结构。

    返回 {tracks: [{id, type, segments: [{id, material_id, start_us, end_us, ...}]}]}
    """
    draft = _open_or_recent(project_name, project_dir, app)
    tracks_out = []
    for t in draft.all_tracks():
        segs = []
        for s in t.segments:
            mat = draft.find_material(s.material_id) or {}
            segs.append({
                "id": s.id,
                "material_id": s.material_id,
                "material_type": mat.get("type", "unknown"),
                "material_path": mat.get("path"),
                "start_us": s.start_us,
                "end_us": s.end_us,
                "duration_us": s.duration_us,
                "start_hms": _hms(s.start_us),
                "end_hms": _hms(s.end_us),
                "source_start_us": s.source_start_us,
                "source_duration_us": s.source_duration_us,
                "speed": s.speed,
                "volume": s.volume,
            })
        tracks_out.append({
            "id": t.id,
            "type": t.type,
            "segments_count": len(segs),
            "segments": segs,
        })
    return {
        "backend": "jianying",
        "project_name": draft.name,
        "duration_us": draft.duration,
        "duration_hms": draft.duration_hms,
        "tracks": tracks_out,
    }


def get_segments_at(timeline: Dict[str, Any], at_us: int) -> List[Dict[str, Any]]:
    """从 get_timeline 的结果中，找出 at_us 时间点上所有轨道的 segment。"""
    out = []
    for t in timeline.get("tracks", []):
        for s in t.get("segments", []):
            if s["start_us"] <= at_us < s["end_us"]:
                out.append({"track_id": t["id"], "track_type": t["type"], **s})
    return out


def find_gaps(timeline: Dict[str, Any], track_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """找出轨道上的空隙（无 segment 的时间段）。

    常用于自动填充转场或检查剪辑连续性。
    """
    gaps = []
    for t in timeline.get("tracks", []):
        if track_id and t["id"] != track_id:
            continue
        if t["type"] not in ("video", "audio"):
            continue
        segs = sorted(t.get("segments", []), key=lambda s: s["start_us"])
        prev_end = 0
        for s in segs:
            if s["start_us"] > prev_end:
                gaps.append({
                    "track_id": t["id"],
                    "track_type": t["type"],
                    "start_us": prev_end,
                    "end_us": s["start_us"],
                    "duration_us": s["start_us"] - prev_end,
                })
            prev_end = max(prev_end, s["end_us"])
        # 末尾到项目时长的空隙
        if prev_end < timeline.get("duration_us", 0):
            gaps.append({
                "track_id": t["id"],
                "track_type": t["type"],
                "start_us": prev_end,
                "end_us": timeline["duration_us"],
                "duration_us": timeline["duration_us"] - prev_end,
            })
    return gaps


def _open_or_recent(project_name, project_dir, app) -> Draft:
    if project_dir:
        return Draft.open(project_dir=project_dir)
    if project_name:
        return Draft.open(project_name=project_name, app=app)
    drafts = P.list_drafts(app=app)
    if not drafts:
        raise FileNotFoundError("未找到任何剪映项目")
    return Draft.open(project_name=drafts[0]["name"], app=app)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) < 2:
        print("用法: python -m cut.jianying.state <project_name> [--materials] [--timeline] [--gaps]")
        sys.exit(1)
    name = sys.argv[1]
    args = sys.argv[2:]
    if "--materials" in args:
        print(json.dumps(list_materials(name), indent=2, ensure_ascii=False))
    elif "--timeline" in args:
        print(json.dumps(get_timeline(name), indent=2, ensure_ascii=False))
    elif "--gaps" in args:
        tl = get_timeline(name)
        print(json.dumps(find_gaps(tl), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(get_state(name), indent=2, ensure_ascii=False))
