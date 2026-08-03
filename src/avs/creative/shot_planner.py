"""Deterministic shot planning from the evidence map."""
from __future__ import annotations

from typing import Any
import json
from pathlib import Path

import jsonschema

_SCHEMA = Path(__file__).resolve().parents[3] / "schemas" / "shot-plan.schema.json"


def plan_shots(
    episode_id: str,
    evidence_map: dict[str, Any],
    *,
    selection: dict[str, Any],
) -> dict[str, Any]:
    patterns = [item["pattern_id"] for item in selection.get("selections", [])]
    if not patterns:
        raise ValueError("Shot Plan 必须引用具体 pattern_id")
    shots: list[dict[str, Any]] = []
    for idx, segment in enumerate(evidence_map.get("segments", []), start=1):
        refs = segment.get("asset_refs", [])
        source_types = {ref.get("source_type") for ref in refs}
        primitive = "kinetic_text" if not refs else (
            "recording_focus_crop" if source_types & {"recording", "video"} else "screenshot_focus"
        )
        shots.append({
            "shot_id": f"shot-{idx:03d}",
            "segment_id": segment["segment_id"],
            "spoken_text": segment.get("spoken_text", ""),
            "duration_seconds": segment["duration_seconds"],
            "primitive": primitive,
            "asset_refs": refs,
            "reference_pattern_ids": list(segment.get("reference_pattern_ids", patterns)),
            "keyframes": [{"time": 0.0, "scale": 1.0}, {"time": segment["duration_seconds"], "scale": 1.08}] if refs else [],
        })
    result = {"episode_id": episode_id, "shots": shots, "excluded_assets": []}
    jsonschema.Draft7Validator(json.loads(_SCHEMA.read_text(encoding="utf-8"))).validate(result)
    return result
