from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from avs.qa.video_release import (
    VideoReleaseReviewError,
    save_video_release_review,
    sha256_file,
    validate_video_release_review,
    verify_video_release_review_current,
)


ROOT = Path(__file__).resolve().parents[1]


def _episode(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    episode = project / "episodes" / "active" / "EP-RELEASE-GATE"
    (project / "schemas").mkdir(parents=True)
    (episode / "renders").mkdir(parents=True)
    schema = ROOT / "schemas" / "video-release-review.schema.json"
    shutil.copy2(schema, project / "schemas" / schema.name)
    video = episode / "renders" / "final-with-captions.mp4"
    video.write_bytes(b"candidate-v1")
    return episode, video


def _payload(video: Path, episode: Path, **overrides: object) -> dict:
    continuous = {
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
    }
    continuous.update(overrides.pop("continuous", {}))
    payload = {
        "reviewed_video": video.relative_to(episode).as_posix(),
        "reviewer": {
            "mode": "actual_artifact_review",
            "reviewer_id": "test-independent-reviewer",
            "inspected_pixels": True,
            "listened_audio": True,
        },
        "continuous_playback_review": continuous,
        "first_pass_memory_summary": "Viewer understood the hook, proof, conflict and next step at 1x.",
        "first_10s_findings": [{"range": "0-10s", "result": "continuous and readable"}],
        "transition_findings": [{"timestamp": "5.0s", "result": "semantic cut; orientation preserved"}],
        "timestamped_findings": [],
        "audio_review_notes": "Listened end-to-end; narration and visible proof stay aligned.",
        "mobile_review_notes": "360x640 preview keeps the key proof readable without pause.",
        "repair_round": 0,
        "final_status": "READY_TO_PUBLISH",
    }
    payload.update(overrides)
    return payload


def test_ready_release_review_is_bound_to_current_video_sha(tmp_path: Path) -> None:
    episode, video = _episode(tmp_path)
    path = save_video_release_review(episode, _payload(video, episode), expected_video=video)

    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["final_status"] == "READY_TO_PUBLISH"
    assert record["video_sha256"] == sha256_file(video)
    assert verify_video_release_review_current(episode, video) == (True, None)


def test_slideshow_hard_fail_cannot_be_marked_ready(tmp_path: Path) -> None:
    episode, video = _episode(tmp_path)
    payload = _payload(video, episode, continuous={"slideshow_like": True})

    with pytest.raises(VideoReleaseReviewError, match="hard fail"):
        validate_video_release_review(episode, payload, expected_video=video)


def test_key_evidence_that_requires_pause_cannot_be_marked_ready(tmp_path: Path) -> None:
    episode, video = _episode(tmp_path)
    payload = _payload(
        video,
        episode,
        continuous={
            "key_evidence_readable_without_pause": False,
            "key_evidence_requires_pause": True,
        },
    )

    with pytest.raises(VideoReleaseReviewError, match="连续观看确认项未通过|hard fail"):
        validate_video_release_review(episode, payload, expected_video=video)


def test_critical_findings_block_ready_status(tmp_path: Path) -> None:
    episode, video = _episode(tmp_path)
    payload = _payload(
        video,
        episode,
        continuous={"critical_findings": ["08.2s proof disappears before comprehension"]},
    )

    with pytest.raises(VideoReleaseReviewError, match="关键观看问题"):
        validate_video_release_review(episode, payload, expected_video=video)


def test_rerender_invalidates_previous_release_review(tmp_path: Path) -> None:
    episode, video = _episode(tmp_path)
    save_video_release_review(episode, _payload(video, episode), expected_video=video)

    video.write_bytes(b"candidate-v2-rerendered")
    valid, reason = verify_video_release_review_current(episode, video)

    assert valid is False
    assert reason is not None
    assert "SHA256" in reason or "重新渲染" in reason


def test_repairing_record_can_be_saved_but_cannot_unlock_delivery(tmp_path: Path) -> None:
    episode, video = _episode(tmp_path)
    payload = _payload(
        video,
        episode,
        final_status="REPAIRING",
        repair_round=1,
        continuous={
            "slideshow_like": True,
            "critical_findings": ["opening feels like a pushed screenshot"],
        },
    )
    save_video_release_review(episode, payload, expected_video=video)

    valid, reason = verify_video_release_review_current(episode, video)
    assert valid is False
    assert reason is not None
    assert "READY_TO_PUBLISH" in reason


def test_review_for_different_video_cannot_unlock_current_candidate(tmp_path: Path) -> None:
    episode, video = _episode(tmp_path)
    other = episode / "renders" / "other.mp4"
    other.write_bytes(b"other")
    payload = _payload(other, episode)

    with pytest.raises(VideoReleaseReviewError, match="不是当前交付视频"):
        validate_video_release_review(episode, payload, expected_video=video)
