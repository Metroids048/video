"""Input material coverage gate."""
from __future__ import annotations

from typing import Any, Iterable


def check_input_coverage(
    manifest: dict[str, Any],
    used_asset_ids: Iterable[str],
    *,
    approved_exclusions: Iterable[str] = (),
) -> dict[str, Any]:
    used = set(used_asset_ids)
    exclusions = set(approved_exclusions)
    missing = [
        asset["asset_id"] for asset in manifest.get("assets", [])
        if asset.get("must_use") and asset.get("asset_id") not in used and asset.get("asset_id") not in exclusions
    ]
    return {
        "passed": not missing,
        "required_count": sum(1 for asset in manifest.get("assets", []) if asset.get("must_use")),
        "used_count": sum(1 for asset in manifest.get("assets", []) if asset.get("must_use") and asset.get("asset_id") in used),
        "missing_asset_ids": missing,
        "approved_exclusions": sorted(exclusions),
    }
