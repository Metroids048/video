from __future__ import annotations

import json
from pathlib import Path

import pytest

from avs.active import active_final_render, active_pilot_review
from avs.models.episode import EpisodeModel, EpisodeValidationError
from avs.pilots import CORE_DIMENSIONS, PILOT_IDS, review_pilots
from avs.workflow import action_for_episode


def _screen_episode(tmp_path: Path) -> tuple[Path, EpisodeModel]:
    ep_dir = tmp_path / "EP-SCREEN"
    ep_dir.mkdir()
    model = EpisodeModel.create("EP-SCREEN", mode="ORIGINAL", production_type="SCREEN_DOCUMENTARY")
    model.save(ep_dir / "episode.json")
    return ep_dir, model


def _manifest(ep_dir: Path) -> None:
    path = ep_dir / "work" / "qa" / "pilots" / "pilot-manifest.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"pilots": {name: {} for name in PILOT_IDS}}), encoding="utf-8")


def _reviewer(reviewer_id: str, *, score: float = 9.0) -> dict[str, object]:
    def score_payload() -> dict[str, float]:
        scores = {dimension: score for dimension in CORE_DIMENSIONS}
        scores["overall"] = score
        return scores
    return {
        "reviewer_id": reviewer_id,
        "reviewer_kind": "agent",
        "reviewed_artifacts": ["actual-mp4", "contact-sheet", "mobile-preview"],
        "variants": {variant: {"scores": score_payload(), "findings": []} for variant in PILOT_IDS},
    }


def test_legacy_episode_defaults_to_standard() -> None:
    assert EpisodeModel.create("EP-LEGACY").production_type == "STANDARD"


def test_invalid_production_type_is_rejected_on_save(tmp_path: Path) -> None:
    model = EpisodeModel.create("EP-BAD", production_type="NOT_A_TYPE")
    with pytest.raises(EpisodeValidationError):
        model.save(tmp_path / "episode.json")


def test_screen_documentary_workflow_starts_at_story_mine(tmp_path: Path) -> None:
    ep_dir, model = _screen_episode(tmp_path)
    action = action_for_episode(ep_dir, model)
    assert action.command == ("story-mine",)


def test_missing_reviewers_blocks_without_fake_scores(tmp_path: Path) -> None:
    ep_dir, _ = _screen_episode(tmp_path)
    _manifest(ep_dir)
    report = review_pilots(ep_dir)
    assert report["decision"] == "BLOCKED"
    assert report["reviewers"] == []


def test_threshold_and_duplicate_reviewer_gate(tmp_path: Path) -> None:
    ep_dir, _ = _screen_episode(tmp_path)
    _manifest(ep_dir)
    with pytest.raises(ValueError, match="独立身份"):
        review_pilots(ep_dir, [_reviewer("r1"), _reviewer("r1")])
    low = _reviewer("r1")
    for reviewer in (low,):
        reviewer["variants"]["primary"]["scores"]["hook"] = 6.9  # type: ignore[index]
    report = review_pilots(ep_dir, [low, _reviewer("r2")], force=True)
    assert report["decision"] == "REJECT"
    assert report["winner"] is None
    assert report["reviews"]["primary"]["scores"]["hook"] < 8


def test_final_render_is_denied_before_pilot_gate(tmp_path: Path) -> None:
    ep_dir, model = _screen_episode(tmp_path)
    with pytest.raises(RuntimeError, match="Pilot Gate"):
        active_final_render(ep_dir, model)


def test_rejected_review_routes_to_bounded_pilot_repair(tmp_path: Path) -> None:
    ep_dir, model = _screen_episode(tmp_path)
    _manifest(ep_dir)
    rejected = _reviewer("r1", score=7.0)
    report = active_pilot_review(ep_dir, model, [rejected, _reviewer("r2", score=7.0)], force=True)
    assert report["decision"] == "REJECT"
    model = EpisodeModel.load(ep_dir / "episode.json")
    action = action_for_episode(ep_dir, model)
    assert action.command == ("pilot-revise",)
