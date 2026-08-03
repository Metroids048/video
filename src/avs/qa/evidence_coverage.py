"""Narration evidence coverage gate."""
from __future__ import annotations

from typing import Any


def check_evidence_coverage(evidence_map: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    known = {asset["asset_id"] for asset in manifest.get("assets", []) if asset.get("status") == "ok"}
    failures: list[dict[str, Any]] = []
    for segment in evidence_map.get("segments", []):
        if not segment.get("evidence_required"):
            continue
        refs = segment.get("asset_refs", [])
        if not refs or any(ref.get("asset_id") not in known for ref in refs):
            failures.append({
                "segment_id": segment.get("segment_id"),
                "spoken_text": segment.get("spoken_text", ""),
                "required_fix": "绑定真实产品素材和 ROI 区域",
            })
    return {"passed": not failures, "failures": failures}
