"""Tests for publishability gate and three-layer QA logic."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def mock_episode_with_quality_config(tmp_path: Path) -> tuple[Path, Path]:
    """Create a mock episode with quality.yaml config."""
    ep_dir = tmp_path / "episodes" / "active" / "EP-TEST"
    ep_dir.mkdir(parents=True, exist_ok=True)

    # Create config directory at project root
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)

    quality_config = {
        "quality": {
            "publishable": {
                "require_non_silent_audio": True,
                "audio_peak_min_dbfs": -45.0,
                "max_total_silence_ratio": 0.40,
                "max_leading_silence_seconds": 1.0,
                "allow_placeholders": False,
                "require_human_visual_approval": True,
            },
            "captions": {
                "max_lines": 2,
                "max_chars_per_line_cjk": 14,
                "max_chars_per_cue_cjk": 24,
            },
            "composition": {
                "landscape_publishable_layouts": ["screen_focus", "screen_stack", "cover"],
                "reject_landscape_contain": True,
            },
        }
    }

    import yaml
    (config_dir / "quality.yaml").write_text(
        yaml.dump(quality_config, allow_unicode=True), encoding="utf-8"
    )

    return tmp_path, ep_dir


def test_publishable_true_with_silent_audio_must_fail(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that publishable=true with silent audio fails QA."""
    # This is a failing test placeholder that will be implemented
    # when we integrate quality.yaml checks into QA
    pytest.skip("待实现：publishable=true + 静音音频必须 QA FAIL")


def test_publishable_true_with_placeholders_must_fail(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that publishable=true with placeholders fails QA."""
    pytest.skip("待实现：publishable=true + 占位卡必须 QA FAIL")


def test_publishable_true_with_oversized_captions_must_fail(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that publishable=true with oversized captions fails QA."""
    pytest.skip("待实现：publishable=true + 字幕超限必须 QA FAIL")


def test_publishable_true_with_landscape_contain_must_fail(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that publishable=true with landscape contain layout fails QA."""
    pytest.skip("待实现：publishable=true + 横屏 contain 黑边必须 QA FAIL")


def test_publishable_true_without_approval_must_block(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that publishable=true without human approval blocks at WAITING_FOR_REVIEW."""
    pytest.skip("待实现：publishable=true + 缺人工批准 → WAITING_FOR_REVIEW")


def test_publishable_true_with_stale_approval_must_fail(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that publishable=true with stale approval hash fails QA."""
    pytest.skip("待实现：批准哈希过期 → QA/delivery FAIL")


def test_publishable_false_skips_publishability_checks(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that publishable=false only requires technical checks."""
    pytest.skip("待实现：publishable=false 只需技术检查通过")


def test_qa_report_fingerprint_triggers_rerun(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that changed inputs trigger QA rerun even without --force."""
    pytest.skip("待实现：input_fingerprint 变化时自动重跑 QA")


def test_delivery_rejects_when_qa_not_passed(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that delivery refuses to run when QA has not passed."""
    pytest.skip("待实现：QA 未通过时 delivery 拒绝")


def test_avs_run_stops_at_waiting_for_review(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that avs run stops at WAITING_FOR_REVIEW when approval missing."""
    pytest.skip("待实现：avs run 在缺人工批准时停在 WAITING_FOR_REVIEW")
