from __future__ import annotations

import json
from pathlib import Path

import pytest

from avs import pilots
from avs.qa import visual_reviewer


def _episode_with_recording(tmp_path: Path, episode_id: str, asset_id: str) -> Path:
    episode_dir = tmp_path / episode_id
    recording = episode_dir / "work" / "prepared" / f"{asset_id}.mp4"
    recording.parent.mkdir(parents=True)
    recording.write_bytes(f"recording-{episode_id}".encode())
    (episode_dir / "work" / "input-manifest.json").write_text(
        json.dumps(
            {
                "episode_id": episode_id,
                "assets": [
                    {
                        "asset_id": asset_id,
                        "source_type": "recording",
                        "working_path": recording.relative_to(episode_dir).as_posix(),
                        "source_path": f"input/{asset_id}.mp4",
                        "must_use": True,
                        "status": "ok",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    analysis_dir = episode_dir / "work" / "analysis"
    analysis_dir.mkdir(parents=True)
    (analysis_dir / "recording-analysis.json").write_text(
        json.dumps(
            {
                "episode_id": episode_id,
                "recordings": [
                    {
                        "asset_id": asset_id,
                        "original_width": 1920,
                        "original_height": 1080,
                        "page_changes": [],
                        "steps": [],
                        "cursor": [],
                        "usable_segments": [{"start": 0.0, "end": 12.0}],
                        "regions": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (analysis_dir / "asset-intelligence.json").write_text(
        json.dumps(
            {
                "episode_id": episode_id,
                "provider": "manual",
                "blocked": False,
                "assets": [
                    {
                        "asset_id": asset_id,
                        "summary": f"{episode_id} page",
                        "product_area": "screen",
                        "visible_facts": [f"fact from {episode_id}"],
                        "regions": [
                            {
                                "region_id": "full-frame",
                                "box": [0.0, 0.0, 1.0, 1.0],
                                "meaning": "complete page",
                                "priority": 1.0,
                            }
                        ],
                        "recommended_uses": ["context"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return episode_dir


def test_current_episode_story_mining_uses_only_current_recording(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    episode_a = _episode_with_recording(tmp_path, "EP-A", "recording-a")
    episode_b = _episode_with_recording(tmp_path, "EP-B", "recording-b")
    package = tmp_path / "vci"
    (package / "structured").mkdir(parents=True)
    (package / "structured" / "content.json").write_text(
        json.dumps({"source_id": "VID-20260812-FDA0", "claims": [], "numbers": []}),
        encoding="utf-8",
    )
    monkeypatch.setattr(pilots, "_vci_package", lambda: package, raising=False)
    monkeypatch.setattr(
        pilots,
        "_source_recording",
        lambda episode_dir: next((episode_dir / "work" / "prepared").glob("recording-*.mp4")),
        raising=False,
    )

    index_a = json.loads(pilots.mine_story(episode_a)["screen_index"].read_text(encoding="utf-8"))
    index_b = json.loads(pilots.mine_story(episode_b)["screen_index"].read_text(encoding="utf-8"))

    assert index_a["episode_id"] == "EP-A"
    assert index_b["episode_id"] == "EP-B"
    assert index_a["source_recording"].startswith("work/prepared/recording-a")
    assert index_b["source_recording"].startswith("work/prepared/recording-b")
    serialized = json.dumps((index_a, index_b), ensure_ascii=False)
    assert "VID-20260812-FDA0" not in serialized
    assert "第一期视频_7x24自动交易" not in serialized


def test_source_order_rejects_non_monotonic_clips() -> None:
    assert hasattr(pilots, "validate_source_order"), "source plan lacks monotonic validation"
    validate_source_order = getattr(pilots, "validate_source_order")
    with pytest.raises(ValueError, match="monotonic"):
        validate_source_order(
            [
                {"source_start": 10.0, "source_end": 20.0},
                {"source_start": 40.0, "source_end": 50.0},
                {"source_start": 25.0, "source_end": 30.0},
            ]
        )

    validate_source_order(
        [
            {"source_start": 10.0, "source_end": 20.0},
            {"source_start": 20.0, "source_end": 30.0},
            {"source_start": 35.0, "source_end": 45.0},
        ]
    )


def test_context_first_landscape_screen_recording_requires_authorized_roi() -> None:
    assert hasattr(pilots, "validate_context_first"), "pilot plan lacks context-first validation"
    validate_context_first = getattr(pilots, "validate_context_first")
    with pytest.raises(ValueError, match="context"):
        validate_context_first(
            [
                {
                    "source_start": 0.0,
                    "source_end": 3.0,
                    "layout": "roi_crop",
                    "allow_destructive_crop": False,
                    "landscape": True,
                }
            ]
        )

    validate_context_first(
        [
            {
                "source_start": 0.0,
                "source_end": 3.0,
                "layout": "fit_full_frame",
                "landscape": True,
            },
            {
                "source_start": 3.0,
                "source_end": 6.0,
                "layout": "roi_crop",
                "allow_destructive_crop": True,
                "roi_authorized": True,
                "landscape": True,
            },
        ]
    )


def test_static_screen_review_does_not_recommend_fake_motion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    frame_a = tmp_path / "frame-a.jpg"
    frame_b = tmp_path / "frame-b.jpg"
    frame_a.write_bytes(b"frame-a")
    frame_b.write_bytes(b"frame-b")
    video = tmp_path / "candidate.mp4"
    video.write_bytes(b"video")

    monkeypatch.setattr(visual_reviewer, "_extract_frames", lambda *args, **kwargs: [frame_a, frame_b, frame_b, frame_b, frame_b])
    monkeypatch.setattr(visual_reviewer, "vision_provider_name", lambda: "none")
    monkeypatch.setattr(visual_reviewer, "_has_large_black_border", lambda *_args: False)
    monkeypatch.setattr(visual_reviewer, "_difference_score", lambda *_args: 0.0)

    report = visual_reviewer.review_video(tmp_path, video_path=video, force=True)
    fixes = " ".join(str(item.get("required_fix", "")) for item in report["failures"])
    assert not any(term in fixes.lower() for term in ("pan", "zoom", "cursor", "ken-burns", "平移", "放大", "鼠标"))
