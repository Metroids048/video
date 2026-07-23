"""src/avs/timeline/csv_export.py — 将 timeline.json 导出为可读 CSV。"""
from __future__ import annotations

import csv
from pathlib import Path

from avs.timeline.models import Timeline


def export_csv(timeline: Timeline, output_path: Path) -> None:
    """将时间线写成 CSV；每行对应一个 clip。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for track in timeline.tracks:
        for clip in track.clips:
            transform_str = ""
            if clip.transform:
                transform_str = clip.transform.get("layout", "")
            rows.append({
                "track_id": track.track_id,
                "kind": track.kind,
                "clip_id": clip.clip_id,
                "start": f"{clip.start:.3f}",
                "duration": f"{clip.duration:.3f}",
                "end": f"{clip.end:.3f}",
                "asset_ref": clip.asset_ref or "",
                "in_point": f"{clip.in_point:.3f}" if clip.in_point is not None else "",
                "out_point": f"{clip.out_point:.3f}" if clip.out_point is not None else "",
                "layout": transform_str,
                "text": clip.text or "",
                "is_placeholder": "TRUE" if (clip.style and clip.style.get("placeholder")) else "FALSE",
            })

    fieldnames = ["track_id", "kind", "clip_id", "start", "duration", "end",
                  "asset_ref", "in_point", "out_point", "layout", "text", "is_placeholder"]
    with output_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
