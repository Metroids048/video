"""src/avs/content/models.py — Script/Storyboard 数据模型。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class ScriptSegment:
    """脚本段落。"""
    def __init__(
        self,
        segment_id: str,
        text: str,
        purpose: str,
        *,
        target_duration: float | None = None,
        visual_hint: str | None = None,
        notes: str | None = None,
    ) -> None:
        self.segment_id = segment_id
        self.text = text
        self.purpose = purpose
        self.target_duration = target_duration
        self.visual_hint = visual_hint
        self.notes = notes

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "text": self.text,
            "purpose": self.purpose,
            "target_duration": self.target_duration,
            "visual_hint": self.visual_hint,
            "notes": self.notes,
        }


class Script:
    """脚本容器。"""
    def __init__(
        self,
        episode_id: str,
        segments: list[ScriptSegment],
        *,
        total_duration_estimate: float | None = None,
    ) -> None:
        self.episode_id = episode_id
        self.segments = segments
        self.total_duration_estimate = total_duration_estimate

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "total_duration_estimate": self.total_duration_estimate,
            "segments": [s.to_dict() for s in self.segments],
            "generated_at": _now_iso(),
        }


class StoryboardShot:
    """分镜镜头。"""
    def __init__(
        self,
        shot_id: str,
        order: int,
        description: str,
        *,
        duration_estimate: float | None = None,
        asset_ref: str | None = None,
        gap: bool = False,
        gap_note: str | None = None,
        visual_treatment: str | None = None,
    ) -> None:
        self.shot_id = shot_id
        self.order = order
        self.description = description
        self.duration_estimate = duration_estimate
        self.asset_ref = asset_ref
        self.gap = gap
        self.gap_note = gap_note
        self.visual_treatment = visual_treatment

    def to_dict(self) -> dict[str, Any]:
        return {
            "shot_id": self.shot_id,
            "order": self.order,
            "description": self.description,
            "duration_estimate": self.duration_estimate,
            "asset_ref": self.asset_ref,
            "gap": self.gap,
            "gap_note": self.gap_note,
            "visual_treatment": self.visual_treatment,
        }


class Storyboard:
    """分镜容器。"""
    def __init__(
        self,
        episode_id: str,
        shots: list[StoryboardShot],
        *,
        asset_gaps: list[str] | None = None,
    ) -> None:
        self.episode_id = episode_id
        self.shots = shots
        self.asset_gaps = asset_gaps or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "shots": [s.to_dict() for s in self.shots],
            "asset_gaps": self.asset_gaps,
            "generated_at": _now_iso(),
        }
