"""Aggregate publishability gate for the active workflow."""
from __future__ import annotations

from typing import Any


def evaluate_publishability(*, input_coverage: dict[str, Any], evidence_coverage: dict[str, Any], pacing: dict[str, Any], visual_review: dict[str, Any], human_approved: bool = False) -> dict[str, Any]:
    checks = {
        "input_coverage": bool(input_coverage.get("passed")),
        "evidence_coverage": bool(evidence_coverage.get("passed")),
        "pacing": bool(pacing.get("passed")),
        "visual_review": bool(visual_review.get("passed")) and not bool(visual_review.get("blocked")),
        "human_approved": bool(human_approved),
    }
    return {"passed": all(checks.values()), "checks": checks, "blocking_reasons": [name for name, passed in checks.items() if not passed]}
