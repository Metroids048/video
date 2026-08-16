"""Deterministic pacing diagnostics that do not pretend to replace full-video review."""
from __future__ import annotations

from typing import Any


SCREENSHOT_PRIMITIVES = {"screenshot_full", "screenshot_stack", "screenshot_compare"}


def check_pacing(shot_plan: dict[str, Any], *, platform: str = "douyin") -> dict[str, Any]:
    """Return pacing diagnostics without turning shot-count/duration into a quality oracle.

    Historical regression: a previous gate rewarded >=4 early shots and rejected screenshot
    shots >3s. That made agents shorten evidence into unreadable 1.x-second fragments and
    encouraged slideshow-like hard cutting. Deterministic QA now checks evidence coverage and
    reports shot diagnostics, while continuity/readability are release-gated by the mandatory
    continuous playback review.
    """
    shots = list(shot_plan.get("shots", []))
    elapsed = 0.0
    early: list[dict[str, Any]] = []
    product_duration = 0.0
    total_duration = 0.0
    long_screenshots: list[str | None] = []
    very_short_shots: list[str | None] = []

    for shot in shots:
        duration = float(shot.get("duration_seconds", 0))
        if elapsed < 10.0:
            early.append(shot)
        if shot.get("asset_refs"):
            product_duration += duration
        if shot.get("primitive") in SCREENSHOT_PRIMITIVES and duration > 3.0:
            long_screenshots.append(shot.get("shot_id"))
        if duration > 0 and duration < 1.5:
            very_short_shots.append(shot.get("shot_id"))
        total_duration += duration
        elapsed += duration

    product_ratio = product_duration / total_duration if total_duration else 0.0
    evidence_ratio_passed = product_ratio >= 0.7

    return {
        "passed": evidence_ratio_passed,
        "product_visual_ratio": round(product_ratio, 4),
        "platform": platform,
        "shot_count": len(shots),
        "first_10s_shot_count": len(early),
        "static_over_3_seconds": long_screenshots,
        "shots_under_1_5_seconds": very_short_shots,
        "shot_count_is_release_metric": False,
        "max_static_duration_is_release_metric": False,
        "continuous_playback_review_required": True,
        "note": (
            "Shot count and static duration are diagnostic only. Do not force cuts to satisfy them; "
            "actual continuity/readability must pass config/video-review.yaml."
        ),
    }
