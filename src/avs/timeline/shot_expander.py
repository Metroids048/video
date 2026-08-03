"""Expand multi-asset segments into observable atomic shots."""
from __future__ import annotations

from typing import Any


def expand_shot(shot: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(atomic_shots, exclusions)`` without silently dropping refs."""
    refs = list(shot.get("asset_refs") or shot.get("asset_ids") or [])
    if not refs:
        return [dict(shot)], []
    base_duration = float(shot.get("duration_seconds", shot.get("duration", 1.0)))
    per_asset = max(base_duration / len(refs), 0.4)
    expanded: list[dict[str, Any]] = []
    for index, ref in enumerate(refs, start=1):
        if isinstance(ref, str):
            asset_ref = {"asset_id": ref, "region_id": "full-frame"}
        else:
            asset_ref = dict(ref)
        item = dict(shot)
        item["shot_id"] = f"{shot.get('shot_id', 'shot')}-{index:02d}"
        item["duration_seconds"] = round(per_asset, 3)
        item["asset_refs"] = [asset_ref]
        expanded.append(item)
    return expanded, []


def expand_shot_plan(plan: dict[str, Any], *, used_asset_ids: set[str] | None = None) -> dict[str, Any]:
    expanded: list[dict[str, Any]] = []
    for shot in plan.get("shots", []):
        shots, _ = expand_shot(shot)
        expanded.extend(shots)
    used = used_asset_ids or {
        str(ref["asset_id"])
        for shot in expanded
        for ref in shot.get("asset_refs", [])
        if isinstance(ref, dict) and ref.get("asset_id")
    }
    exclusions = list(plan.get("excluded_assets", []))
    return {"episode_id": plan.get("episode_id"), "shots": expanded, "excluded_assets": exclusions, "used_asset_ids": sorted(used)}
