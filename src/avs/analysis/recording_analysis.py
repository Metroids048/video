"""Recording metadata analysis with a conservative, provider-free baseline."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import jsonschema

_SCHEMA = Path(__file__).resolve().parents[3] / "schemas" / "recording-analysis.schema.json"


def _page_changes(path: Path) -> list[dict[str, Any]]:
    executable = shutil.which("ffmpeg")
    if executable is None:
        return []
    command = [
        executable, "-hide_banner", "-i", str(path),
        "-vf", "select='gt(scene,0.25)',showinfo", "-f", "null", "-",
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
    changes: list[dict[str, Any]] = []
    for match in re.finditer(r"pts_time:([0-9.]+)", result.stderr):
        changes.append({"timestamp": float(match.group(1)), "reason": "scene_change"})
    return changes


def analyze_recordings(
    episode_dir: Path,
    *,
    manifest: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    output = episode_dir / "work" / "analysis" / "recording-analysis.json"
    if output.is_file() and not force:
        return json.loads(output.read_text(encoding="utf-8"))
    if manifest is None:
        manifest = json.loads((episode_dir / "work" / "input-manifest.json").read_text(encoding="utf-8"))
    recordings: list[dict[str, Any]] = []
    for asset in manifest.get("assets", []):
        if asset.get("source_type") not in {"recording", "video"}:
            continue
        source = episode_dir / str(asset.get("working_path"))
        changes = _page_changes(source) if source.is_file() else []
        duration = float(asset.get("duration") or 0)
        boundaries = [0.0, *(item["timestamp"] for item in changes), duration]
        usable = [
            {"start": start, "end": end}
            for start, end in zip(boundaries, boundaries[1:])
            if end > start
        ]
        recordings.append({
            "asset_id": asset["asset_id"],
            "original_width": asset.get("original_width"),
            "original_height": asset.get("original_height"),
            "page_changes": changes,
            "steps": [],
            "cursor": [],
            "usable_segments": usable,
            "regions": [],
            "analysis_status": "metadata_and_scene_changes",
        })
    doc = {"episode_id": manifest["episode_id"], "recordings": recordings}
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc
