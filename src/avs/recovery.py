"""Transactional Episode reset for resumable workflows."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from avs.models.episode import EpisodeModel


@dataclass(frozen=True)
class ResetResult:
    old_status: str
    new_status: str


_KEEP_AFTER_INGEST = {"input-manifest.json", "prepared"}
_DOWNSTREAM_DIRS = {"analysis", "content", "director", "pilots", "qa"}
_DOWNSTREAM_FILES = {"timeline.json", "captions.srt", "pilot-manifest.json", "pilot-review.json"}


def reset_episode(ep_dir: Path, model: EpisodeModel, target_status: str) -> ResetResult:
    """Reset state and downstream artifacts atomically enough for local files.

    Inputs and ingest work copies survive an INGESTED reset; generated analysis,
    director, pilot, timeline and render artifacts are staged then removed. If
    saving episode.json fails, the staged tree is restored and the status object
    remains unchanged on disk.
    """
    if target_status not in {"CREATED", "INGESTED", "CONTENT_READY"}:
        raise ValueError(f"不允许的 reset 目标: {target_status}")
    old_status = model.status
    staging = ep_dir / ".reset-staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()
    moved: list[tuple[Path, Path]] = []

    def stage(path: Path) -> None:
        if not path.exists():
            return
        target = staging / path.relative_to(ep_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(target))
        moved.append((target, path))

    try:
        if target_status == "CREATED":
            for child in ep_dir.iterdir():
                if child.name not in {"episode.json", "input", ".reset-staging"}:
                    stage(child)
        else:
            for name in _DOWNSTREAM_DIRS:
                stage(ep_dir / "work" / name)
            for name in _DOWNSTREAM_FILES:
                stage(ep_dir / "work" / name)
            if target_status == "INGESTED":
                stage(ep_dir / "renders")
            else:
                stage(ep_dir / "renders")
                stage(ep_dir / "work" / "input-manifest.json")

        allowed = {"ingest"} if target_status == "INGESTED" else set()
        if target_status == "CONTENT_READY":
            allowed = {"ingest", "content"}
        model.retain_completed_stages(allowed)
        model._data["blocked"] = False
        model._data["blocked_stage"] = None
        model._data["last_error"] = None
        model._data["status"] = target_status
        model.save(ep_dir / "episode.json")
    except Exception:
        for staged, original in reversed(moved):
            if staged.exists():
                original.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(staged), str(original))
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    return ResetResult(old_status=old_status, new_status=target_status)
