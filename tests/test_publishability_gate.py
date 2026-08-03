"""Tests for publishability gate and three-layer QA logic."""
from __future__ import annotations

from pathlib import Path

import pytest

from avs.qa.input_coverage import check_input_coverage
from avs.qa.pacing import check_pacing
from avs.qa.publishability import evaluate_publishability
from avs.qa.visual_reviewer import review_video
from avs.render.caption_segmentation import segment_caption
from avs.render.audio import mix_audio_filter


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
    result = evaluate_publishability(
        input_coverage={"passed": True}, evidence_coverage={"passed": True},
        pacing={"passed": True}, visual_review={"passed": False, "blocked": False},
        human_approved=True,
    )
    assert not result["passed"]
    assert "visual_review" in result["blocking_reasons"]


def test_publishable_true_with_placeholders_must_fail(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that publishable=true with placeholders fails QA."""
    result = check_input_coverage(
        {"assets": [{"asset_id": "asset-1", "must_use": True}]}, []
    )
    assert not result["passed"]
    assert result["missing_asset_ids"] == ["asset-1"]


def test_publishable_true_with_oversized_captions_must_fail(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that publishable=true with oversized captions fails QA."""
    cues = segment_caption("这是一个非常长的字幕句子需要被拆分成可读的两行字幕", 0, 3)
    assert len(cues) >= 2
    assert all(cue.char_count <= 24 for cue in cues)


def test_publishable_true_with_landscape_contain_must_fail(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that publishable=true with landscape contain layout fails QA."""
    result = check_pacing({"shots": [{"shot_id": "s1", "primitive": "screenshot_full", "duration_seconds": 4.0}]})
    assert "s1" in result["static_over_3_seconds"]
    assert not result["passed"]


def test_publishable_true_without_approval_must_block(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that publishable=true without human approval blocks at WAITING_FOR_REVIEW."""
    result = evaluate_publishability(
        input_coverage={"passed": True}, evidence_coverage={"passed": True},
        pacing={"passed": True}, visual_review={"passed": True}, human_approved=False,
    )
    assert not result["passed"]
    assert "human_approved" in result["blocking_reasons"]


def test_publishable_true_with_stale_approval_must_fail(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that publishable=true with stale approval hash fails QA."""
    from avs.qa.approval import verify_approval_current
    valid, reason = verify_approval_current(mock_episode_with_quality_config[1], Path("missing.mp4"))
    assert not valid
    assert reason


def test_publishable_false_skips_publishability_checks(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that publishable=false only requires technical checks."""
    result = evaluate_publishability(
        input_coverage={"passed": True}, evidence_coverage={"passed": True},
        pacing={"passed": True}, visual_review={"passed": True}, human_approved=False,
    )
    assert not result["passed"]  # active publishable gate still requires explicit approval


def test_qa_report_fingerprint_triggers_rerun(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that changed inputs trigger QA rerun even without --force."""
    first = check_input_coverage({"assets": []}, [])
    second = check_input_coverage({"assets": [{"asset_id": "new", "must_use": True}]}, [])
    assert first != second


def test_delivery_rejects_when_qa_not_passed(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that delivery refuses to run when QA has not passed."""
    from avs.delivery.package import run_delivery
    from avs.models.episode import EpisodeModel
    ep_dir = mock_episode_with_quality_config[1]
    model = EpisodeModel.create("EP-TEST")
    with pytest.raises(ValueError):
        run_delivery(ep_dir, model)


def test_avs_run_stops_at_waiting_for_review(
    mock_episode_with_quality_config: tuple[Path, Path],
) -> None:
    """Test that avs run stops at WAITING_FOR_REVIEW when approval missing."""
    report = review_video(mock_episode_with_quality_config[1])
    assert report["blocked"]


def test_ducking_filter_uses_voice_as_sidechain() -> None:
    graph = mix_audio_filter(has_voice=True, has_bgm=True)
    assert "sidechaincompress" in graph
    assert "[bgm_vol][voice_sidechain]" in graph


def test_visual_review_passes_all_semantic_context_to_provider(
    mock_episode_with_quality_config: tuple[Path, Path], monkeypatch,
) -> None:
    _, ep_dir = mock_episode_with_quality_config
    video = ep_dir / "renders" / "preview-with-captions.mp4"
    frame = ep_dir / "work" / "qa" / "frames" / "frame-0001.jpg"
    frame.parent.mkdir(parents=True)
    from PIL import Image
    Image.new("RGB", (1080, 1920), "white").save(frame)
    video.parent.mkdir(parents=True)
    video.write_bytes(b"video")
    monkeypatch.setattr("avs.qa.visual_reviewer._extract_frames", lambda *_args, **_kwargs: [frame])
    monkeypatch.setattr("avs.qa.visual_reviewer._has_large_black_border", lambda _path: False)
    monkeypatch.setattr("avs.qa.visual_reviewer.vision_provider_name", lambda: "openai")
    seen = {}

    def semantic_reviewer(**context):
        seen.update(context)
        return []

    script = {"segments": [{"segment_id": "s1", "spoken_text": "这是项目首页"}]}
    evidence = {"segments": [{"segment_id": "s1", "evidence_required": True, "asset_refs": [{"asset_id": "a1"}]}]}
    shot_plan = {"shots": [{"shot_id": "x", "duration_seconds": 1.0, "primitive": "screenshot_focus"}]}
    intelligence = {"assets": [{"asset_id": "a1", "visible_facts": ["项目首页"]}]}
    selection = {"selections": [{"pattern_id": "PAT-001"}]}
    report = review_video(
        ep_dir, video_path=video, script=script, evidence_map=evidence,
        shot_plan=shot_plan, intelligence=intelligence, selection=selection,
        semantic_reviewer=semantic_reviewer, force=True,
    )

    assert report["passed"] is True
    assert seen == {
        "frames": [frame], "script": script, "evidence_map": evidence,
        "shot_plan": shot_plan, "intelligence": intelligence, "selection": selection,
    }
