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
        source_refs: list[str] | None = None,
        status: str = "draft",
        notes: str | None = None,
    ) -> None:
        self.segment_id = segment_id
        self.text = text
        self.purpose = purpose
        self.target_duration = target_duration
        self.visual_hint = visual_hint
        self.source_refs = source_refs or []
        self.status = status
        self.notes = notes

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "text": self.text,
            "purpose": self.purpose,
            "target_duration": self.target_duration,
            "visual_hint": self.visual_hint,
            "source_refs": self.source_refs,
            "status": self.status,
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
        scene_id: str,
        script_segment_ids: list[str],
        duration: float,
        visual_type: str,
        *,
        asset_ids: list[str] | None = None,
        caption: str = "",
        motion_template: str | None = None,
        missing_assets: list[str] | None = None,
        notes: str | None = None,
    ) -> None:
        self.scene_id = scene_id
        self.script_segment_ids = script_segment_ids
        self.duration = duration
        self.visual_type = visual_type
        self.asset_ids = asset_ids or []
        self.caption = caption
        self.motion_template = motion_template
        self.missing_assets = missing_assets or []
        self.notes = notes

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "script_segment_ids": self.script_segment_ids,
            "duration": self.duration,
            "visual_type": self.visual_type,
            "asset_ids": self.asset_ids,
            "caption": self.caption,
            "motion_template": self.motion_template,
            "missing_assets": self.missing_assets,
            "notes": self.notes,
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
