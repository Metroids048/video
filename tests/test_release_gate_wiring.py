"""Canonical wiring tests for the content-addressed video release gate."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from avs.delivery.package import run_delivery
from avs.models.episode import EpisodeModel
from avs.qa.report import run_qa
from avs.qa.video_release import save_video_release_review, sha256_file
from avs.workflow import action_for_episode


ROOT = Path(__file__).resolve().parents[1]


def _episode(tmp_path: Path, *, production_type: str = "STANDARD") -> tuple[Path, EpisodeModel, Path, Path]:
    project = tmp_path / "project"
    ep_dir = project / "episodes" / "active" / "EP-RELEASE-WIRING"
    for relative in ("renders", "work/prepared", "work/qa", "delivery"):
        (ep_dir / relative).mkdir(parents=True, exist_ok=True)
    schemas = project / "schemas"
    schemas.mkdir(parents=True)
    for name in (
        "episode.schema.json",
        "qa-report.schema.json",
        "video-release-review.schema.json",
    ):
        shutil.copy2(ROOT / "schemas" / name, schemas / name)

    final_video = ep_dir / "renders" / "final-with-captions.mp4"
    final_video.write_bytes(b"candidate-v1")
    source = ep_dir / "work" / "prepared" / "source.mp4"
    source.write_bytes(b"source-v1")
    (ep_dir / "work" / "input-manifest.json").write_text(
        json.dumps({"episode_id": "EP-RELEASE-WIRING", "assets": []}),
        encoding="utf-8",
    )

    model = EpisodeModel.create(
        "EP-RELEASE-WIRING",
        production_type=production_type,
    )
    for status in (
        "INGESTED",
        "CONTENT_READY",
        "ASSETS_READY",
        "TIMELINE_READY",
        "ROUGH_CUT_READY",
    ):
        model.transition(status)
    stages = (
        ("story-mine", "direct", "pilot", "pilot-review", "final-render")
        if production_type == "SCREEN_DOCUMENTARY"
        else ("analyze", "plan", "preview", "visual-review", "final-render")
    )
    for stage in stages:
        model.complete_stage(stage)
    model.save(ep_dir / "episode.json")
    return ep_dir, model, final_video, source


def _release_payload(ep_dir: Path, final_video: Path, source: Path) -> dict:
    return {
        "reviewed_video": final_video.relative_to(ep_dir).as_posix(),
        "reviewer": {
            "mode": "actual_artifact_review",
            "reviewer_id": "independent-release-reviewer",
            "inspected_pixels": True,
            "listened_audio": True,
        },
        "source_fidelity_review": {
            "compared_source_to_final": True,
            "full_frame_integrity_checked": True,
            "spatial_continuity_checked": True,
            "temporal_continuity_checked": True,
            "opening_context_checked": True,
            "all_crop_events_explicitly_authorized": True,
            "unauthorized_destructive_crop_detected": False,
            "source_context_loss_detected": False,
            "spatial_continuity_broken": False,
            "temporal_continuity_broken": False,
            "opening_mid_action_or_partial_frame": False,
            "source_fidelity_findings": [],
            "source_artifacts": [{
                "path": source.relative_to(ep_dir).as_posix(),
                "sha256": sha256_file(source),
                "role": "primary_video_source",
            }],
        },
        "continuous_playback_review": {
            "watched_start_to_end_1x": True,
            "first_pass_without_pause_for_comprehension": True,
            "first_10s_dense_review_completed": True,
            "key_evidence_readable_without_pause": True,
            "audio_listened_end_to_end": True,
            "mobile_360x640_reviewed": True,
            "transition_scan_completed": True,
            "slideshow_like": False,
            "static_screenshot_motion_dominant": False,
            "rapid_dark_light_switching": False,
            "unmotivated_abrupt_cuts": False,
            "abrupt_context_loss": False,
            "visual_motion_without_semantic_reason": False,
            "audio_visual_semantic_mismatch": False,
            "caption_or_overlay_blocks_evidence": False,
            "key_evidence_requires_pause": False,
            "known_critical_issue_at_delivery": False,
            "critical_findings": [],
        },
        "first_pass_memory_summary": "The current candidate was understandable at 1x.",
        "first_10s_findings": [{"range": "0-10s", "result": "readable"}],
        "transition_findings": [{"timestamp": "1.0s", "result": "continuous"}],
        "timestamped_findings": [],
        "audio_review_notes": "Listened to the current mix end-to-end.",
        "mobile_review_notes": "Key evidence remained readable at 360x640.",
        "repair_round": 0,
        "final_status": "READY_TO_PUBLISH",
    }


def _assert_qa_rejects_before_checks(
    monkeypatch: pytest.MonkeyPatch,
    ep_dir: Path,
) -> None:
    monkeypatch.setattr(
        "avs.qa.report.inspect_timeline",
        lambda _path: (_ for _ in ()).throw(AssertionError("QA ran before release gate")),
    )
    with pytest.raises(ValueError, match="Release Review|发布验收"):
        run_qa(ep_dir, ep_dir.name, publishable=True, force=True)


def _assert_delivery_rejects_before_copy(
    monkeypatch: pytest.MonkeyPatch,
    ep_dir: Path,
    model: EpisodeModel,
) -> None:
    model.transition("QA_PASSED")
    monkeypatch.setattr(
        "avs.delivery.package._qa_report",
        lambda _ep_dir: {"passed": True, "human_approved": True},
    )
    monkeypatch.setattr("avs.delivery.package._require_passing_creative_review", lambda *_args: None)
    monkeypatch.setattr("avs.qa.approval.load_approval", lambda _ep_dir: {"approved": True})
    monkeypatch.setattr("avs.qa.approval.verify_approval_current", lambda *_args: (True, None))
    monkeypatch.setattr(
        "avs.delivery.package._copy_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("delivery copied files before release gate")
        ),
    )
    with pytest.raises(ValueError, match="Release Review|发布验收"):
        run_delivery(ep_dir, model)


@pytest.mark.parametrize("production_type", ["STANDARD", "SCREEN_DOCUMENTARY"])
def test_missing_release_review_blocks_workflow(
    tmp_path: Path,
    production_type: str,
) -> None:
    ep_dir, model, _, _ = _episode(tmp_path, production_type=production_type)

    action = action_for_episode(ep_dir, model)

    assert action.stage == "release-review"
    assert action.command == ("release-review",)


def test_missing_release_review_blocks_qa(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ep_dir, _, _, _ = _episode(tmp_path)
    _assert_qa_rejects_before_checks(monkeypatch, ep_dir)


def test_missing_release_review_blocks_delivery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ep_dir, model, _, _ = _episode(tmp_path)
    _assert_delivery_rejects_before_copy(monkeypatch, ep_dir, model)


@pytest.mark.parametrize("production_type", ["STANDARD", "SCREEN_DOCUMENTARY"])
def test_stale_release_review_returns_workflow_to_release_review(
    tmp_path: Path,
    production_type: str,
) -> None:
    ep_dir, model, final_video, source = _episode(tmp_path, production_type=production_type)
    save_video_release_review(
        ep_dir,
        _release_payload(ep_dir, final_video, source),
        expected_video=final_video,
    )
    final_video.write_bytes(b"candidate-v2-rerendered")

    action = action_for_episode(ep_dir, model)

    assert action.stage == "release-review"
    assert action.command == ("release-review",)


def test_stale_release_review_blocks_qa(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ep_dir, _, final_video, source = _episode(tmp_path)
    save_video_release_review(
        ep_dir,
        _release_payload(ep_dir, final_video, source),
        expected_video=final_video,
    )
    final_video.write_bytes(b"candidate-v2-rerendered")

    _assert_qa_rejects_before_checks(monkeypatch, ep_dir)


def test_stale_release_review_blocks_delivery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ep_dir, model, final_video, source = _episode(tmp_path)
    save_video_release_review(
        ep_dir,
        _release_payload(ep_dir, final_video, source),
        expected_video=final_video,
    )
    final_video.write_bytes(b"candidate-v2-rerendered")

    _assert_delivery_rejects_before_copy(monkeypatch, ep_dir, model)
