from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from avs.qa.pacing import check_pacing
from avs.render.ffmpeg import _caption_filter
from avs.render.primitives import primitive_filter


ROOT = Path(__file__).resolve().parents[1]


def test_caption_filter_uses_explicit_portrait_playres_and_safe_zone(tmp_path: Path) -> None:
    graph = _caption_filter(tmp_path / "captions.srt")

    assert "original_size=1080x1920" in graph
    assert "FontSize=50" in graph
    assert "MarginV=260" in graph
    assert "Alignment=2" in graph


def test_screenshot_full_preserves_wide_screen_evidence() -> None:
    graph = primitive_filter("screenshot_full", duration=3.0)

    assert "force_original_aspect_ratio=decrease" in graph
    assert "pad=1080:1920" in graph
    assert "force_original_aspect_ratio=increase" not in graph


def test_legacy_ep01_visual_review_cannot_create_a_parallel_pass_path(tmp_path: Path) -> None:
    episode = tmp_path / "EP-QUALITY-REGRESSION"
    qa_dir = episode / "work" / "qa"
    qa_dir.mkdir(parents=True)
    (qa_dir / "visual-review.input.json").write_text(
        json.dumps({"passed": True, "scores": {"overall": 10}}), encoding="utf-8"
    )

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "mark_ep01_visual_review.py"), str(episode)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "visual-review.input.json is no longer a release gate" in combined
    assert "video-release-review.input.json" in combined
    assert not (qa_dir / "visual-review.json").exists()
    assert not (qa_dir / "video-release-review.json").exists()


def test_legacy_ep01_review_rejects_keyframes_without_canonical_full_watch_record(tmp_path: Path) -> None:
    episode = tmp_path / "EP-CONTINUOUS-REVIEW"
    qa_dir = episode / "work" / "qa"
    qa_dir.mkdir(parents=True)
    (episode / "candidate.mp4").write_bytes(b"not-a-real-video")
    (episode / "contact.jpg").write_bytes(b"frame")

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "mark_ep01_visual_review.py"), str(episode)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "video-release-review.input.json" in combined
    assert "full 1x watch" in combined
    assert not (qa_dir / "video-release-review.json").exists()


def test_pacing_does_not_reward_forced_shot_churn() -> None:
    shot_plan = {
        "shots": [
            {
                "shot_id": "proof-a",
                "primitive": "screenshot_full",
                "duration_seconds": 5.0,
                "asset_refs": [{"asset_id": "a"}],
            },
            {
                "shot_id": "proof-b",
                "primitive": "screenshot_full",
                "duration_seconds": 5.0,
                "asset_refs": [{"asset_id": "b"}],
            },
        ]
    }

    result = check_pacing(shot_plan, platform="douyin")

    assert result["passed"] is True
    assert result["first_10s_shot_count"] == 2
    assert result["shot_count_is_release_metric"] is False
    assert result["max_static_duration_is_release_metric"] is False
    assert result["continuous_playback_review_required"] is True


def test_video_review_config_hard_fails_real_ep01_regressions() -> None:
    config = yaml.safe_load((ROOT / "config" / "video-review.yaml").read_text(encoding="utf-8"))
    review = config["video_review"]

    assert review["required_review_views"]["continuous_playback_1x"]["required"] is True
    assert review["required_review_views"]["first_second_review"]["required"] is True
    assert review["hard_fail_conditions"]["abrupt_or_discontinuous_opening"]["fail"] is True
    assert review["hard_fail_conditions"]["slideshow_feel"]["fail"] is True
    assert review["hard_fail_conditions"]["static_screenshot_pan_zoom_dominant"]["fail"] is True
    assert review["hard_fail_conditions"]["key_evidence_requires_pause"]["fail"] is True
    assert review["hard_fail_conditions"]["unreadable_evidence_due_to_short_dwell"]["fail"] is True
    assert review["hard_fail_conditions"]["rapid_dark_light_switching"]["fail"] is True
    assert review["continuity_rules"]["no_forced_cut_rate"] is True
    assert review["continuity_rules"]["no_max_shot_duration_as_quality_target"] is True
    assert review["pacing_rules"]["never_compress_to_hit_duration_metric"] is True
    assert review["repair_loop"]["full_rewatch_after_every_repair"] is True
    assert review["delivery_gate"]["delivery_requires_zero_known_critical_findings"] is True
    assert review["delivery_gate"]["current_sha256_match_required"] is True


def test_pre_delivery_prompt_requires_full_playback_machine_gate_and_repair_loop() -> None:
    prompt = (ROOT / "docs" / "creator-os" / "video-pre-delivery-qa-prompt.md").read_text(encoding="utf-8")

    assert "Watch the CURRENT candidate from 0:00 to the end at normal 1x speed" in prompt
    assert "FIRST SECOND + FIRST 10 SECONDS DENSE REVIEW" in prompt
    assert "contact sheets" in prompt
    assert "slideshow" in prompt.lower()
    assert "Ken Burns" in prompt
    assert "dark Binance -> white backend -> dark Binance" in prompt
    assert "key evidence requires pause" in prompt
    assert "MUST repair" in prompt
    assert "video-release-review.input.json" in prompt
    assert "validate_video_release_review.py" in prompt
    assert "Maximum 3 repair rounds" in prompt
    assert "current SHA256 matches the validated release-review record" in prompt
