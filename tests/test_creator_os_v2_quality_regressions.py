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


def test_ep01_visual_review_cannot_self_approve_without_external_review(tmp_path: Path) -> None:
    episode = tmp_path / "EP-QUALITY-REGRESSION"
    (episode / "work" / "qa").mkdir(parents=True)

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "mark_ep01_visual_review.py"), str(episode)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert not (episode / "work" / "qa" / "visual-review.json").exists()


def test_ep01_visual_review_rejects_keyframes_without_full_continuous_watch(tmp_path: Path) -> None:
    episode = tmp_path / "EP-CONTINUOUS-REVIEW"
    qa_dir = episode / "work" / "qa"
    qa_dir.mkdir(parents=True)
    (episode / "candidate.mp4").write_bytes(b"not-a-real-video")
    (episode / "contact.jpg").write_bytes(b"frame")

    score_keys = {
        "hook",
        "story",
        "pacing",
        "evidence",
        "visual",
        "human_tone",
        "audio",
        "captions",
        "reference_fidelity",
        "overall",
    }
    payload = {
        "reviewer": {
            "mode": "actual_artifact_review",
            "inspected_pixels": True,
            "reviewer_id": "regression-test",
        },
        "reviewed_video": "candidate.mp4",
        "reviewed_artifacts": ["contact.jpg"],
        "scores": {key: 9.0 for key in score_keys},
        "timestamped_findings": [],
        "passed": True,
        "blocked": False,
    }
    (qa_dir / "visual-review.input.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "mark_ep01_visual_review.py"), str(episode)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "continuous_playback_review is required" in (result.stdout + result.stderr)
    assert not (qa_dir / "visual-review.json").exists()


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


def test_video_review_config_hard_fails_slideshow_and_unreadable_evidence() -> None:
    config = yaml.safe_load((ROOT / "config" / "video-review.yaml").read_text(encoding="utf-8"))
    review = config["video_review"]

    assert review["required_review_views"]["continuous_playback_1x"]["required"] is True
    assert review["hard_fail_conditions"]["slideshow_feel"]["fail"] is True
    assert review["hard_fail_conditions"]["static_screenshot_pan_zoom_dominant"]["fail"] is True
    assert review["hard_fail_conditions"]["key_evidence_requires_pause"]["fail"] is True
    assert review["hard_fail_conditions"]["rapid_dark_light_switching"]["fail"] is True
    assert review["continuity_rules"]["no_forced_cut_rate"] is True
    assert review["pacing_rules"]["never_compress_to_hit_duration_metric"] is True
    assert review["repair_loop"]["full_rewatch_after_every_repair"] is True
    assert review["delivery_gate"]["delivery_requires_zero_known_critical_findings"] is True
