"""Tests for human visual approval with content-addressed binding."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from avs.qa.approval import (
    create_approval,
    load_approval,
    save_approval,
    sha256_file,
    verify_approval_current,
)


@pytest.fixture
def mock_episode_dir(tmp_path: Path) -> Path:
    """Create a mock episode directory with schemas."""
    ep_dir = tmp_path / "episodes" / "active" / "EP-TEST"
    ep_dir.mkdir(parents=True, exist_ok=True)

    # Create schemas directory at project root
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir(exist_ok=True)

    # Copy visual-approval schema
    schema_content = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "visual-approval.schema.json",
        "title": "VisualApproval",
        "type": "object",
        "required": [
            "episode_id",
            "approved",
            "reviewer",
            "video_path",
            "video_sha256",
            "reviewed_at",
            "checklist",
        ],
        "properties": {
            "episode_id": {"type": "string"},
            "approved": {"type": "boolean"},
            "reviewer": {"type": "string"},
            "video_path": {"type": "string"},
            "video_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            "reviewed_at": {"type": "string", "format": "date-time"},
            "checklist": {
                "type": "object",
                "required": [
                    "hook_clear_within_3s",
                    "captions_readable",
                    "composition_acceptable",
                    "audio_acceptable",
                    "no_placeholders",
                    "facts_and_rights_checked",
                ],
                "properties": {
                    "hook_clear_within_3s": {"type": "boolean"},
                    "captions_readable": {"type": "boolean"},
                    "composition_acceptable": {"type": "boolean"},
                    "audio_acceptable": {"type": "boolean"},
                    "no_placeholders": {"type": "boolean"},
                    "facts_and_rights_checked": {"type": "boolean"},
                },
            },
            "notes": {"type": ["string", "null"]},
        },
    }
    (schemas_dir / "visual-approval.schema.json").write_text(
        json.dumps(schema_content, indent=2), encoding="utf-8"
    )

    return ep_dir


@pytest.fixture
def mock_video(mock_episode_dir: Path) -> Path:
    """Create a mock video file inside episode renders directory."""
    renders_dir = mock_episode_dir / "renders"
    renders_dir.mkdir(parents=True, exist_ok=True)
    video = renders_dir / "preview-with-motion.mp4"
    video.write_bytes(b"fake video content")
    return video


def test_sha256_file(mock_video: Path) -> None:
    """Test file hashing."""
    hash1 = sha256_file(mock_video)
    assert len(hash1) == 64
    assert hash1 == sha256_file(mock_video)  # Deterministic


def test_create_approval_success(mock_episode_dir: Path, mock_video: Path) -> None:
    """Test creating a valid approval."""
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


def test_create_approval_missing_video(mock_episode_dir: Path) -> None:
    """Test creating approval for non-existent video fails."""
    with pytest.raises(FileNotFoundError, match="视频不存在"):
        create_approval(
            mock_episode_dir,
            "EP-TEST",
            "Reviewer",
            mock_episode_dir / "nonexistent.mp4",
        )


def test_create_approval_invalid_checklist(mock_episode_dir: Path, mock_video: Path) -> None:
    """Test creating approval with invalid checklist fails."""
    with pytest.raises(ValueError, match="checklist 必须包含且仅包含以下键"):
        create_approval(
            mock_episode_dir,
            "EP-TEST",
            "Reviewer",
            mock_video,
            checklist={"invalid_key": True},
        )


def test_create_approval_false_checklist_item(mock_episode_dir: Path, mock_video: Path) -> None:
    """Test creating approval with false checklist item fails."""
    checklist = {
        "hook_clear_within_3s": True,
        "captions_readable": False,  # This should block
        "composition_acceptable": True,
        "audio_acceptable": True,
        "no_placeholders": True,
        "facts_and_rights_checked": True,
    }
    with pytest.raises(ValueError, match="任一 checklist 项为 false 时不得 approved=True"):
        create_approval(mock_episode_dir, "EP-TEST", "Reviewer", mock_video, checklist=checklist)


def test_save_and_load_approval(mock_episode_dir: Path, mock_video: Path) -> None:
    """Test saving and loading approval."""
    approval = create_approval(mock_episode_dir, "EP-TEST", "Reviewer", mock_video)
    saved_path = save_approval(mock_episode_dir, approval)

    assert saved_path.is_file()
    assert saved_path == mock_episode_dir / "delivery" / "visual-approval.json"

    loaded = load_approval(mock_episode_dir)
    assert loaded is not None
    assert loaded["episode_id"] == approval["episode_id"]
    assert loaded["video_sha256"] == approval["video_sha256"]


def test_load_approval_missing(mock_episode_dir: Path) -> None:
    """Test loading missing approval returns None."""
    assert load_approval(mock_episode_dir) is None


def test_verify_approval_current_success(mock_episode_dir: Path, mock_video: Path) -> None:
    """Test verifying current approval succeeds when hash matches."""
    approval = create_approval(mock_episode_dir, "EP-TEST", "Reviewer", mock_video)
    save_approval(mock_episode_dir, approval)

    is_valid, error = verify_approval_current(mock_episode_dir, mock_video)
    assert is_valid is True
    assert error is None


def test_verify_approval_current_missing(mock_episode_dir: Path, mock_video: Path) -> None:
    """Test verifying approval fails when approval missing."""
    is_valid, error = verify_approval_current(mock_episode_dir, mock_video)
    assert is_valid is False
    assert "缺少人工视觉批准文件" in error


def test_verify_approval_current_hash_mismatch(mock_episode_dir: Path, mock_video: Path) -> None:
    """Test verifying approval fails when video hash changes."""
    # Create and save approval for original video
    approval = create_approval(mock_episode_dir, "EP-TEST", "Reviewer", mock_video)
    save_approval(mock_episode_dir, approval)

    # Modify video content
    mock_video.write_bytes(b"modified video content")

    is_valid, error = verify_approval_current(mock_episode_dir, mock_video)
    assert is_valid is False
    assert "视频已变更" in error
    assert "批准哈希" in error


def test_verify_approval_current_video_missing(mock_episode_dir: Path, mock_video: Path) -> None:
    """Test verifying approval fails when video no longer exists."""
    approval = create_approval(mock_episode_dir, "EP-TEST", "Reviewer", mock_video)
    save_approval(mock_episode_dir, approval)

    # Remove video
    mock_video.unlink()

    is_valid, error = verify_approval_current(mock_episode_dir, mock_video)
    assert is_valid is False
    assert "最终视频不存在" in error
