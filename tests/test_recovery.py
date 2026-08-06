"""Transactional reset behavior for resumable Active Episodes."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from avs.models.episode import EpisodeModel
from avs.paths import create_episode_skeleton


def _blocked_episode(tmp_path: Path) -> tuple[Path, EpisodeModel]:
    ep_dir = tmp_path / "EP-RESET"
    ep_dir.mkdir()
    create_episode_skeleton(ep_dir)
    model = EpisodeModel.create("EP-RESET")
    model.transition("INGESTED")
    model.complete_stage("ingest")
    model.transition("CONTENT_READY")
    model.complete_stage("analyze")
    model.complete_stage("plan")
    model.complete_stage("preview")
    model.block("视觉审核未通过", stage="visual-review")
    model.save(ep_dir / "episode.json")
    return ep_dir, model


def _write(path: Path, content: str = "marker") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_reset_to_ingested_keeps_only_ingest_and_removes_downstream_artifacts(tmp_path: Path) -> None:
    from avs.recovery import reset_episode

    ep_dir, model = _blocked_episode(tmp_path)
    _write(ep_dir / "input" / "images" / "original.txt")
    _write(ep_dir / "work" / "input-manifest.json")
    _write(ep_dir / "work" / "prepared" / "source.txt")
    _write(ep_dir / "work" / "analysis" / "asset-intelligence.json")
    _write(ep_dir / "work" / "content" / "script.json")
    _write(ep_dir / "work" / "timeline.json")
    _write(ep_dir / "renders" / "preview-with-captions.mp4")

    result = reset_episode(ep_dir, model, "INGESTED")

    reloaded = EpisodeModel.load(ep_dir / "episode.json")
    assert result.old_status == "CONTENT_READY"
    assert result.new_status == "INGESTED"
    assert reloaded.completed_stages == ["ingest"]
    assert reloaded.blocked is False
    assert reloaded.blocked_stage is None
    assert (ep_dir / "input" / "images" / "original.txt").is_file()
    assert (ep_dir / "work" / "input-manifest.json").is_file()
    assert (ep_dir / "work" / "prepared" / "source.txt").is_file()
    assert not (ep_dir / "work" / "analysis").exists()
    assert not (ep_dir / "work" / "content" / "script.json").exists()
    assert not (ep_dir / "work" / "timeline.json").exists()
    assert not (ep_dir / "renders" / "preview-with-captions.mp4").exists()
    assert not (ep_dir / ".reset-staging").exists()


def test_reset_restores_artifacts_when_episode_save_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from avs.recovery import reset_episode

    ep_dir, model = _blocked_episode(tmp_path)
    analysis = ep_dir / "work" / "analysis" / "asset-intelligence.json"
    _write(analysis, json.dumps({"blocked": True}))
    before = (ep_dir / "episode.json").read_text(encoding="utf-8")

    def fail_save(_path: Path) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(model, "save", fail_save)

    with pytest.raises(OSError, match="disk full"):
        reset_episode(ep_dir, model, "INGESTED")

    assert analysis.is_file()
    assert (ep_dir / "episode.json").read_text(encoding="utf-8") == before
    assert not (ep_dir / ".reset-staging").exists()
