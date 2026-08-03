"""Build and validate the narration -> fact -> asset -> ROI trace."""
from __future__ import annotations

from typing import Any
import json
from pathlib import Path

import jsonschema

_SCHEMA = Path(__file__).resolve().parents[3] / "schemas" / "evidence-map.schema.json"


def build_evidence_map(
    episode_id: str,
    script: dict[str, Any],
    *,
    intelligence: dict[str, Any],
) -> dict[str, Any]:
    by_id = {asset["asset_id"]: asset for asset in intelligence.get("assets", [])}
    known = set(by_id)
    segments: list[dict[str, Any]] = []
    for segment in script.get("segments", []):
        refs = []
        for raw_ref in segment.get("asset_refs", []):
            ref = dict(raw_ref)
            asset = by_id.get(ref.get("asset_id"), {})
            source_type = asset.get("metadata", {}).get("source_type")
            if source_type:
                ref["source_type"] = source_type
            refs.append(ref)
        if segment.get("evidence_required"):
            if not refs or any(ref.get("asset_id") not in known for ref in refs):
                raise ValueError(f"{segment.get('segment_id')} 缺少真实素材证据")
        segments.append({
            "segment_id": segment["segment_id"],
            "spoken_text": segment.get("spoken_text", segment.get("text", "")),
            "purpose": segment.get("purpose", ""),
            "duration_seconds": float(segment.get("duration_seconds", 1.0)),
            "evidence_required": bool(segment.get("evidence_required", False)),
            "asset_refs": refs,
            "reference_pattern_ids": list(segment.get("reference_pattern_ids", [])),
        })
    result = {"episode_id": episode_id, "segments": segments}
    jsonschema.Draft7Validator(json.loads(_SCHEMA.read_text(encoding="utf-8"))).validate(result)
    return result
