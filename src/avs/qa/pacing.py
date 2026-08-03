"""Platform pacing gate independent of subjective visual semantics."""
from __future__ import annotations

from typing import Any


def check_pacing(shot_plan: dict[str, Any], *, platform: str = "douyin") -> dict[str, Any]:
    shots = list(shot_plan.get("shots", []))
    static = [
        shot for shot in shots
        if shot.get("primitive") in {"screenshot_full", "screenshot_stack", "screenshot_compare"}
        and float(shot.get("duration_seconds", 0)) > 3.0
    ]
    elapsed = 0.0
    early: list[dict[str, Any]] = []
    product_duration = 0.0
    total_duration = 0.0
    for shot in shots:
        duration = float(shot.get("duration_seconds", 0))
        if elapsed < 10.0:
            early.append(shot)
        if shot.get("asset_refs"):
            product_duration += duration
        total_duration += duration
        elapsed += duration
    product_ratio = product_duration / total_duration if total_duration else 0.0
    return {
        "passed": not static and len(early) >= (4 if platform == "douyin" else 2) and product_ratio >= 0.7,
        "static_over_3_seconds": [shot.get("shot_id") for shot in static],
        "early_change_count": len(early),
        "product_visual_ratio": round(product_ratio, 4),
        "platform": platform,
    }
