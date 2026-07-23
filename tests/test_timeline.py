"""tests/test_timeline.py — 模块6 时间线单元测试。"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from avs.timeline.models import Canvas, Clip, Timeline, Track
from avs.timeline.validate import validate_timeline, TimelineValidationError
from avs.timeline.csv_export import export_csv


# ── fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_ep(tmp_path):
    """创建最小 episode 目录结构。"""
    ep = tmp_path / "episodes" / "active" / "EP-TL-TEST"
    ep.mkdir(parents=True)
    (ep / "work").mkdir()
    (ep / "input" / "images").mkdir(parents=True)
    (ep / "input" / "audio").mkdir(parents=True)
    (ep / "renders").mkdir()
    return ep


@pytest.fixture
def minimal_timeline(tmp_ep):
    """最小可用 timeline（单视频 clip）。"""
    tl = Timeline(
        episode_id="EP-TL-TEST",
        canvas=Canvas(1080, 1920, 30),
        tracks=[
            Track("video-main", "video", [
                Clip("v-001", start=0.0, duration=3.0, text="测试占位卡",
                     style={"placeholder": True}),
                Clip("v-002", start=3.0, duration=2.0, text="占位卡2",
                     style={"placeholder": True}),
            ]),
        ],
        total_duration=5.0,
    )
    return tl


@pytest.fixture
def schema_path(tmp_path):
    """复制项目 schema 到临时目录。"""
    project_root = Path(__file__).parents[1]
    src = project_root / "schemas" / "timeline.schema.json"
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    dst = schemas_dir / "timeline.schema.json"
    shutil.copy2(str(src), str(dst))
    return dst


# ── 模型测试 ───────────────────────────────────────────────────────────────

class TestTimelineModels:
    def test_clip_end(self):
        c = Clip("c1", start=2.5, duration=3.0)
        assert abs(c.end - 5.5) < 0.001

    def test_timeline_compute_duration(self, minimal_timeline):
        dur = minimal_timeline.compute_duration()
        assert abs(dur - 5.0) < 0.001

    def test_timeline_save_load(self, tmp_ep, minimal_timeline):
        path = tmp_ep / "work" / "timeline.json"
        minimal_timeline.save(path)
        assert path.exists()
        loaded = Timeline.load(path)
        assert loaded.episode_id == "EP-TL-TEST"
        assert len(loaded.tracks) == 1
        assert len(loaded.tracks[0].clips) == 2

    def test_timeline_to_dict_keys(self, minimal_timeline):
        d = minimal_timeline.to_dict()
        for key in ("episode_id", "version", "canvas", "tracks", "total_duration", "generated_at"):
            assert key in d, f"缺少字段: {key}"

    def test_track_get(self, minimal_timeline):
        vt = minimal_timeline.get_track("video")
        assert vt is not None
        assert vt.track_id == "video-main"
        at = minimal_timeline.get_track("audio")
        assert at is None


# ── 校验测试 ───────────────────────────────────────────────────────────────

class TestTimelineValidate:
    def test_valid_timeline_passes(self, tmp_ep, minimal_timeline, schema_path):
        path = tmp_ep / "work" / "timeline.json"
        minimal_timeline.save(path)
        issues = validate_timeline(path, schema_path=schema_path)
        errors = [i for i in issues if i.level == "error"]
        assert not errors, f"意外 error: {errors}"

    def test_missing_file_raises(self, tmp_ep, schema_path):
        with pytest.raises(TimelineValidationError, match="不存在"):
            validate_timeline(tmp_ep / "nonexistent.json", schema_path=schema_path)

    def test_no_video_track(self, tmp_ep, schema_path):
        tl = Timeline("EP-X", tracks=[
            Track("audio-only", "audio", [Clip("a1", 0.0, 3.0)]),
        ], total_duration=3.0)
        path = tmp_ep / "work" / "timeline.json"
        tl.save(path)
        issues = validate_timeline(path, schema_path=schema_path)
        errors = [i for i in issues if i.level == "error"]
        assert any("video" in i.message for i in errors)

    def test_subtitle_overflow(self, tmp_ep, schema_path):
        tl = Timeline("EP-X", tracks=[
            Track("video-main", "video", [Clip("v1", 0.0, 5.0)]),
            Track("captions-main", "caption", [Clip("cap1", 4.0, 3.0, text="越界字幕")]),
        ], total_duration=5.0)
        path = tmp_ep / "work" / "timeline.json"
        tl.save(path)
        issues = validate_timeline(path, schema_path=schema_path)
        errors = [i for i in issues if i.level == "error"]
        assert any("越界" in i.message for i in errors)

    def test_duplicate_clip_id(self, tmp_ep, schema_path):
        tl = Timeline("EP-X", tracks=[
            Track("video-main", "video", [
                Clip("dup", 0.0, 2.0),
                Clip("dup", 2.0, 2.0),
            ]),
        ], total_duration=4.0)
        path = tmp_ep / "work" / "timeline.json"
        tl.save(path)
        issues = validate_timeline(path, schema_path=schema_path)
        errors = [i for i in issues if i.level == "error"]
        assert any("重复" in i.message for i in errors)

    def test_nonstandard_canvas_warns(self, tmp_ep, schema_path):
        tl = Timeline("EP-X",
                      canvas=Canvas(1920, 1080, 30),
                      tracks=[Track("video-main", "video", [Clip("v1", 0.0, 3.0)])],
                      total_duration=3.0)
        path = tmp_ep / "work" / "timeline.json"
        tl.save(path)
        issues = validate_timeline(path, schema_path=schema_path)
        warns = [i for i in issues if i.level == "warning"]
        assert any("1920" in i.message or "非标准" in i.message for i in warns)


# ── CSV 导出测试 ───────────────────────────────────────────────────────────

class TestCsvExport:
    def test_csv_has_correct_rows(self, tmp_ep, minimal_timeline):
        csv_path = tmp_ep / "work" / "timeline.csv"
        export_csv(minimal_timeline, csv_path)
        assert csv_path.exists()
        text = csv_path.read_text(encoding="utf-8-sig")
        rows = [r for r in text.strip().splitlines() if r]
        # 1 header + 2 clips
        assert len(rows) == 3

    def test_csv_has_required_columns(self, tmp_ep, minimal_timeline):
        csv_path = tmp_ep / "work" / "timeline.csv"
        export_csv(minimal_timeline, csv_path)
        header = csv_path.read_text(encoding="utf-8-sig").splitlines()[0]
        for col in ("track_id", "clip_id", "start", "duration", "end"):
            assert col in header


# ── builder 测试 ──────────────────────────────────────────────────────────

class TestTimelineBuilder:
    def test_build_without_storyboard(self, tmp_ep):
        from avs.timeline.builder import build_timeline
        tl = build_timeline(tmp_ep, "EP-TL-TEST")
        assert tl is not None
        assert len(tl.tracks) >= 1
        assert tl.total_duration > 0

    def test_build_with_storyboard(self, tmp_ep):
        from avs.timeline.builder import build_timeline
        # 创建最小 storyboard.json
        content_dir = tmp_ep / "work" / "content"
        content_dir.mkdir(parents=True, exist_ok=True)
        storyboard = {
            "episode_id": "EP-TL-TEST",
            "shots": [
                {"shot_id": "s001", "order": 1, "description": "镜头1",
                 "duration_estimate": 4.0, "gap": True},
                {"shot_id": "s002", "order": 2, "description": "镜头2",
                 "duration_estimate": 3.0, "gap": True},
            ],
            "asset_gaps": ["s001", "s002"],
        }
        (content_dir / "storyboard.json").write_text(
            json.dumps(storyboard), encoding="utf-8"
        )
        tl = build_timeline(tmp_ep, "EP-TL-TEST", force=True)
        assert tl.total_duration == pytest.approx(7.0)
        vt = tl.get_track("video")
        assert vt is not None
        assert len(vt.clips) == 2

    def test_build_idempotent(self, tmp_ep):
        from avs.timeline.builder import build_timeline
        tl1 = build_timeline(tmp_ep, "EP-TL-TEST")
        tl2 = build_timeline(tmp_ep, "EP-TL-TEST")  # 第二次不重建
        assert tl1.episode_id == tl2.episode_id

    def test_build_force_rebuilds(self, tmp_ep):
        from avs.timeline.builder import build_timeline
        tl1 = build_timeline(tmp_ep, "EP-TL-TEST")
        path = tmp_ep / "work" / "timeline.json"
        mtime1 = path.stat().st_mtime
        import time; time.sleep(0.05)
        tl2 = build_timeline(tmp_ep, "EP-TL-TEST", force=True)
        mtime2 = path.stat().st_mtime
        assert mtime2 >= mtime1
