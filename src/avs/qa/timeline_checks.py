"""Timeline semantic QA helpers."""
from __future__ import annotations

import json
from pathlib import Path

from avs.timeline.validate import validate_timeline


def inspect_timeline(path: Path) -> dict:
    if not path.is_file():
        return {"errors": ["timeline.json 不存在"], "warnings": [], "placeholder_count": 0, "planned_audio": False}
    try:
        issues = validate_timeline(path)
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "errors": [str(exc)], "warnings": [], "placeholder_count": 0,
            "planned_audio": False, "total_duration": 0.0,
        }
    placeholders = sum(
        1 for track in data.get("tracks", []) for clip in track.get("clips", [])
        if (clip.get("style") or {}).get("placeholder")
    )
    planned_audio = any(track.get("kind") == "audio" and track.get("clips") for track in data.get("tracks", []))
    return {
        "errors": [issue.message for issue in issues if issue.level == "error"],
        "warnings": [issue.message for issue in issues if issue.level == "warning"],
        "placeholder_count": placeholders,
        "planned_audio": planned_audio,
        "total_duration": float(data.get("total_duration") or 0),
    }
