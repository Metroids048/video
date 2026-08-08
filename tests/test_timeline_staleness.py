"""A rebuilt storyboard must not keep serving the previous timeline.

`timeline.json` is derived from the storyboard.  Existence-based idempotence
let a changed storyboard render with stale shot durations: every upstream
artifact showed the new cut, the pipeline reported success, and only the video
still had the old one.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from avs.timeline.builder import _timeline_is_stale, build_timeline


def _touch(path: Path, *, offset: float) -> None:
    """Set mtime relative to now so ordering is explicit rather than timing-dependent."""
    stamp = time.time() + offset
    os.utime(path, (stamp, stamp))


def _episode(tmp_path: Path, durations: list[float]) -> Path:
    ep_dir = tmp_path / "episodes" / "active" / "EP-STALE"
    (ep_dir / "work" / "content").mkdir(parents=True)
    (ep_dir / "work" / "prepared").mkdir(parents=True)
    storyboard = {
        "episode_id": "EP-STALE",
        "shots": [
            {
                "scene_id": f"shot-{index + 1:03d}",
                "script_segment_ids": [f"seg-{index + 1:03d}"],
                "duration": value,
                "visual_type": "motion_graphic",
                "asset_ids": [],
                "asset_refs": [],
                "caption": f"第 {index + 1} 句",
                "motion_template": "InfoCard",
                "missing_assets": [],
            }
            for index, value in enumerate(durations)
        ],
        "asset_gaps": [],
    }
    (ep_dir / "work" / "content" / "storyboard.json").write_text(
        json.dumps(storyboard, ensure_ascii=False), encoding="utf-8",
    )
    (ep_dir / "work" / "asset-manifest.json").write_text(
        json.dumps({"episode_id": "EP-STALE", "assets": []}), encoding="utf-8",
    )
    return ep_dir


def _durations(ep_dir: Path) -> list[float]:
    timeline = json.loads((ep_dir / "work" / "timeline.json").read_text(encoding="utf-8"))
    return [
        round(float(clip["duration"]), 2)
        for track in timeline["tracks"]
        if track["kind"] == "video"
        for clip in track["clips"]
    ]


def test_stale_detection_compares_mtimes(tmp_path: Path) -> None:
    timeline = tmp_path / "timeline.json"
    source = tmp_path / "storyboard.json"
    timeline.write_text("{}", encoding="utf-8")
    source.write_text("{}", encoding="utf-8")

    _touch(timeline, offset=-10)
    _touch(source, offset=0)
    assert _timeline_is_stale(timeline, [source]) is True

    _touch(timeline, offset=0)
    _touch(source, offset=-10)
    assert _timeline_is_stale(timeline, [source]) is False


def test_missing_timeline_counts_as_stale(tmp_path: Path) -> None:
    assert _timeline_is_stale(tmp_path / "absent.json", []) is True


def test_absent_source_is_ignored(tmp_path: Path) -> None:
    timeline = tmp_path / "timeline.json"
    timeline.write_text("{}", encoding="utf-8")
    assert _timeline_is_stale(timeline, [tmp_path / "never-written.json"]) is False


def test_updated_storyboard_rebuilds_timeline_without_force(tmp_path: Path) -> None:
    ep_dir = _episode(tmp_path, [4.0, 4.0, 4.0])
    build_timeline(ep_dir, "EP-STALE")
    assert _durations(ep_dir) == [4.0, 4.0, 4.0]

    # Rewrite the storyboard the way `plan` does when an Agent script changes it.
    storyboard_path = ep_dir / "work" / "content" / "storyboard.json"
    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
    for shot, value in zip(storyboard["shots"], [3.2, 1.8, 5.5]):
        shot["duration"] = value
    storyboard_path.write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")
    _touch(ep_dir / "work" / "timeline.json", offset=-10)
    _touch(storyboard_path, offset=0)

    build_timeline(ep_dir, "EP-STALE")

    assert _durations(ep_dir) == [3.2, 1.8, 5.5], "storyboard 更新后必须重建时间线"


def test_unchanged_storyboard_keeps_timeline_untouched(tmp_path: Path) -> None:
    ep_dir = _episode(tmp_path, [4.0, 3.6])
    build_timeline(ep_dir, "EP-STALE")
    timeline_path = ep_dir / "work" / "timeline.json"
    _touch(ep_dir / "work" / "content" / "storyboard.json", offset=-10)
    _touch(timeline_path, offset=0)
    before = timeline_path.read_text(encoding="utf-8")

    build_timeline(ep_dir, "EP-STALE")

    assert timeline_path.read_text(encoding="utf-8") == before, "未变更时应保持幂等"
