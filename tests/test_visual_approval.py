"""Tests for human visual approval with content-addressed release-review binding."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from avs.qa.approval import (
    create_approval,
    load_approval,
    save_approval,
    sha256_file,
    verify_approval_current,
)
from avs.qa.video_release import save_video_release_review


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def mock_episode_dir(tmp_path: Path) -> Path:
    project = tmp_path
    ep_dir = project / "episodes" / "active" / "EP-TEST"
    ep_dir.mkdir(parents=True, exist_ok=True)

    schemas_dir = project / "schemas"
    schemas_dir.mkdir(exist_ok=True)
    for name in ("visual-approval.schema.json", "video-release-review.schema.json"):
        shutil.copy2(ROOT / "schemas" / name, schemas_dir / name)
    return ep_dir


def _release_payload(ep_dir: Path, video: Path, source: Path) -> dict:
    return {
        "reviewed_video": video.relative_to(ep_dir).as_posix(),
        "reviewer": {
            "mode": "actual_artifact_review",
            "reviewer_id": "test-independent-reviewer",
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
            "source_artifacts": [
                {
                    "path": source.relative_to(ep_dir).as_posix(),
                    "sha256": sha256_file(source),
                    "role": "primary_screen_recording",
                }
            ],
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
        "first_pass_memory_summary": "Viewer can follow the story and proof at 1x without replay.",
        "first_10s_findings": [{"range": "0-10s", "result": "readable and continuous"}],
        "transition_findings": [{"timestamp": "2.0s", "result": "semantic cut"}],
        "timestamped_findings": [],
        "audio_review_notes": "Audio listened end-to-end and aligned with proof.",
        "mobile_review_notes": "Key proof readable at 360x640.",
        "repair_round": 0,
        "final_status": "READY_TO_PUBLISH",
    }


@pytest.fixture
def mock_video(mock_episode_dir: Path) -> Path:
    renders_dir = mock_episode_dir / "renders"
    renders_dir.mkdir(parents=True, exist_ok=True)
    source = mock_episode_dir / "work" / "prepared" / "source-screen.mp4"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"full source screen content")
    video = renders_dir / "preview-with-motion.mp4"
    video.write_bytes(b"fake video content")
    save_video_release_review(
        mock_episode_dir,
        _release_payload(mock_episode_dir, video, source),
        expected_video=video,
    )
    return video


def test_sha256_file(mock_video: Path) -> None:
    hash1 = sha256_file(mock_video)
    assert len(hash1) == 64
    assert hash1 == sha256_file(mock_video)


def test_create_approval_success(mock_episode_dir: Path, mock_video: Path) -> None:
    approval = create_approval(
        mock_episode_dir,
        "EP-TEST",
        "Human Reviewer",
        mock_video,
        notes="Looks good",
    )

    assert approval["episode_id"] == "EP-TEST"
    assert approval["approved"] is True
    assert approval["reviewer"] == "Human Reviewer"
    assert approval["video_sha256"] == sha256_file(mock_video)
    assert "reviewed_at" in approval
    assert all(approval["checklist"].values())


def test_create_approval_requires_current_release_review(mock_episode_dir: Path, mock_video: Path) -> None:
    (mock_episode_dir / "work" / "qa" / "video-release-review.json").unlink()

    with pytest.raises(ValueError, match="视频发布验收未通过"):
        create_approval(mock_episode_dir, "EP-TEST", "Reviewer", mock_video)


def test_create_approval_missing_video(mock_episode_dir: Path) -> None:
    with pytest.raises(FileNotFoundError, match="视频不存在"):
        create_approval(
            mock_episode_dir,
            "EP-TEST",
            "Reviewer",
            mock_episode_dir / "nonexistent.mp4",
        )


def test_create_approval_invalid_checklist(mock_episode_dir: Path, mock_video: Path) -> None:
    with pytest.raises(ValueError, match="checklist 必须包含且仅包含以下键"):
        create_approval(
            mock_episode_dir,
            "EP-TEST",
            "Reviewer",
            mock_video,
            checklist={"invalid_key": True},
        )


def test_create_approval_false_checklist_item(mock_episode_dir: Path, mock_video: Path) -> None:
    checklist = {
        "hook_clear_within_3s": True,
        "captions_readable": False,
        "composition_acceptable": True,
        "audio_acceptable": True,
        "no_placeholders": True,
        "facts_and_rights_checked": True,
    }
    with pytest.raises(ValueError, match="任一 checklist 项为 false 时不得 approved=True"):
        create_approval(mock_episode_dir, "EP-TEST", "Reviewer", mock_video, checklist=checklist)


def test_save_and_load_approval(mock_episode_dir: Path, mock_video: Path) -> None:
    approval = create_approval(mock_episode_dir, "EP-TEST", "Reviewer", mock_video)
    saved_path = save_approval(mock_episode_dir, approval)

    assert saved_path.is_file()
    assert saved_path == mock_episode_dir / "delivery" / "visual-approval.json"

    loaded = load_approval(mock_episode_dir)
    assert loaded is not None
    assert loaded["episode_id"] == approval["episode_id"]
    assert loaded["video_sha256"] == approval["video_sha256"]


def test_load_approval_missing(mock_episode_dir: Path) -> None:
    assert load_approval(mock_episode_dir) is None


def test_verify_approval_current_success(mock_episode_dir: Path, mock_video: Path) -> None:
    approval = create_approval(mock_episode_dir, "EP-TEST", "Reviewer", mock_video)
    save_approval(mock_episode_dir, approval)

    is_valid, error = verify_approval_current(mock_episode_dir, mock_video)
    assert is_valid is True
    assert error is None


def test_verify_approval_current_missing(mock_episode_dir: Path, mock_video: Path) -> None:
    is_valid, error = verify_approval_current(mock_episode_dir, mock_video)
    assert is_valid is False
    assert error is not None
    assert "缺少人工视觉批准文件" in error


def test_verify_approval_current_hash_mismatch(mock_episode_dir: Path, mock_video: Path) -> None:
    approval = create_approval(mock_episode_dir, "EP-TEST", "Reviewer", mock_video)
    save_approval(mock_episode_dir, approval)

    mock_video.write_bytes(b"modified video content")

    is_valid, error = verify_approval_current(mock_episode_dir, mock_video)
    assert is_valid is False
    assert error is not None
    assert "SHA256" in error or "重新渲染" in error or "视频已变更" in error


def test_verify_approval_current_video_missing(mock_episode_dir: Path, mock_video: Path) -> None:
    approval = create_approval(mock_episode_dir, "EP-TEST", "Reviewer", mock_video)
    save_approval(mock_episode_dir, approval)

    mock_video.unlink()

    is_valid, error = verify_approval_current(mock_episode_dir, mock_video)
    assert is_valid is False
    assert error is not None
    assert "最终视频不存在" in error


def test_release_review_change_invalidates_saved_approval(mock_episode_dir: Path, mock_video: Path) -> None:
    approval = create_approval(mock_episode_dir, "EP-TEST", "Reviewer", mock_video)
    save_approval(mock_episode_dir, approval)

    review_path = mock_episode_dir / "work" / "qa" / "video-release-review.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review["mobile_review_notes"] = "changed after approval"
    review_path.write_text(json.dumps(review), encoding="utf-8")

    valid, reason = verify_approval_current(mock_episode_dir, mock_video)
    assert valid is False
    assert reason is not None
    assert "Fingerprint" in reason or "指纹" in reason or "Release Review" in reason
