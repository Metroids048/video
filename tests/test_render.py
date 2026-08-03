"""tests/test_render.py — 模块6 渲染单元测试（FFmpeg 可选）。"""
from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import patch
import json
import importlib.util

import pytest
from click.testing import CliRunner

from avs.timeline.models import Canvas, Clip, Timeline, Track
from avs.render.captions import build_srt, _seconds_to_srt_time, has_subtitle_overflow
from avs.render.ffmpeg import _caption_filter
from avs.cli import main
from avs.models.episode import EpisodeModel
from avs.paths import create_episode_skeleton


# ── SRT 生成测试 ──────────────────────────────────────────────────────────

class TestBuildSrt:
    def test_basic_srt(self, tmp_path):
        tl = Timeline("EP-X", tracks=[
            Track("video-main", "video", [Clip("v1", 0.0, 10.0)]),
            Track("captions-main", "caption", [
                Clip("c1", 0.0, 3.0, text="第一条字幕"),
                Clip("c2", 3.5, 4.0, text="第二条字幕"),
            ]),
        ], total_duration=10.0)
        srt_path = tmp_path / "captions.srt"
        count = build_srt(tl, srt_path)
        assert count == 2
        content = srt_path.read_text(encoding="utf-8")
        assert "第一条字幕" in content
        assert "第二条字幕" in content
        assert "00:00:00,000" in content

    def test_empty_caption_track(self, tmp_path):
        tl = Timeline("EP-X", tracks=[
            Track("video-main", "video", [Clip("v1", 0.0, 5.0)]),
        ], total_duration=5.0)
        srt_path = tmp_path / "captions.srt"
        count = build_srt(tl, srt_path)
        assert count == 0
        assert srt_path.read_text() == ""

    def test_graphic_card_text_is_not_duplicated_as_caption(self, tmp_path):
        tl = Timeline("EP-X", tracks=[
            Track("captions-main", "caption", [
                Clip("c1", 0.0, 3.0, text="动效卡已经显示这句话"),
                Clip("c2", 3.0, 3.0, text="普通画面保留字幕"),
            ]),
            Track("graphics-main", "graphic", [
                Clip("g1", 0.0, 3.0, text="动效卡已经显示这句话", style={"motion_template": "HookTitle"}),
            ]),
        ], total_duration=6.0)
        srt_path = tmp_path / "captions.srt"

        build_srt(tl, srt_path)

        content = srt_path.read_text(encoding="utf-8")
        assert "动效卡已经显示这句话" not in content
        assert "普通画面保留字幕" in content

    def test_caption_burn_style_uses_bottom_safe_zone(self, tmp_path):
        graph = _caption_filter(tmp_path / "captions.srt")
        assert "FontSize=15" in graph
        assert "MarginV=40" in graph
        assert "Alignment=2" in graph

    def test_overflow_truncated(self, tmp_path):
        # 字幕超出 total_duration 应被截断
        tl = Timeline("EP-X", tracks=[
            Track("video-main", "video", [Clip("v1", 0.0, 5.0)]),
            Track("captions-main", "caption", [
                Clip("c1", 4.0, 3.0, text="越界字幕"),  # end=7.0 > 5.0
            ]),
        ], total_duration=5.0)
        srt_path = tmp_path / "captions.srt"
        count = build_srt(tl, srt_path)
        assert count == 1  # 截断后仍有字幕
        content = srt_path.read_text()
        # 时间戳结束不超过 5.0
        assert "00:00:07" not in content

    def test_no_overflow_in_valid_srt(self, tmp_path):
        srt_content = "1\n00:00:00,000 --> 00:00:03,000\n正常字幕\n\n"
        srt_path = tmp_path / "captions.srt"
        srt_path.write_text(srt_content, encoding="utf-8")
        violations = has_subtitle_overflow(srt_path, total_duration=10.0)
        assert violations == []

    def test_overflow_detected(self, tmp_path):
        srt_content = "1\n00:00:09,000 --> 00:00:12,000\n越界字幕\n\n"
        srt_path = tmp_path / "captions.srt"
        srt_path.write_text(srt_content, encoding="utf-8")
        violations = has_subtitle_overflow(srt_path, total_duration=10.0)
        assert len(violations) == 1


class TestSrtTimecode:
    def test_zero(self):
        assert _seconds_to_srt_time(0.0) == "00:00:00,000"

    def test_exact_minutes(self):
        assert _seconds_to_srt_time(90.0) == "00:01:30,000"

    def test_with_ms(self):
        assert _seconds_to_srt_time(3.5) == "00:00:03,500"

    def test_hours(self):
        assert _seconds_to_srt_time(3661.0) == "01:01:01,000"


# ── 渲染测试（FFmpeg 可用时运行，否则 mock）─────────────────────────────────

class TestRenderRoughCut:
    """核心渲染逻辑测试，FFmpeg 不可用时 mock subprocess。"""

    def _make_timeline(self, ep_dir: Path) -> Timeline:
        return Timeline(
            episode_id="EP-RENDER-TEST",
            canvas=Canvas(1080, 1920, 30),
            tracks=[
                Track("video-main", "video", [
                    Clip("v-001", 0.0, 2.0, text="占位1", style={"placeholder": True}),
                    Clip("v-002", 2.0, 2.0, text="占位2", style={"placeholder": True}),
                ]),
            ],
            total_duration=4.0,
        )

    @pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg 不可用")
    def test_render_produces_mp4(self, tmp_path):
        """有 ffmpeg 时：实际生成两个 MP4。"""
        ep_dir = tmp_path / "ep"
        ep_dir.mkdir()
        (ep_dir / "work").mkdir()
        (ep_dir / "renders").mkdir()
        tl = self._make_timeline(ep_dir)
        tl.save(ep_dir / "work" / "timeline.json")

        from avs.render import render_rough_cut
        result = render_rough_cut(ep_dir, tl, force=True)
        assert result["preview_clean"].exists()
        assert result["preview_with_captions"].exists()
        assert result["preview_clean"].stat().st_size > 0

    @pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="ffmpeg 不可用")
    def test_invalid_cache_is_rebuilt(self, tmp_path):
        ep_dir = tmp_path / "ep"
        ep_dir.mkdir()
        (ep_dir / "work").mkdir()
        renders = ep_dir / "renders"
        renders.mkdir()
        tl = self._make_timeline(ep_dir)

        # 预置假 MP4
        clean = renders / "preview-clean.mp4"
        cap = renders / "preview-with-captions.mp4"
        clean.write_bytes(b"fake")
        cap.write_bytes(b"fake")

        from avs.render import render_rough_cut
        result = render_rough_cut(ep_dir, tl, force=False)
        assert result["preview_clean"].read_bytes() != b"fake"

    @pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="ffmpeg 不可用")
    def test_valid_render_cache_is_idempotent(self, tmp_path):
        ep_dir = tmp_path / "ep"
        ep_dir.mkdir()
        (ep_dir / "work").mkdir()
        (ep_dir / "renders").mkdir()
        tl = self._make_timeline(ep_dir)
        from avs.render import render_rough_cut
        first = render_rough_cut(ep_dir, tl, force=True)
        mtime = first["preview_clean"].stat().st_mtime_ns
        second = render_rough_cut(ep_dir, tl, force=False)
        assert second["preview_clean"].stat().st_mtime_ns == mtime

    def test_render_error_no_ffmpeg(self, tmp_path):
        """ffmpeg 不可用时抛出 RenderError。"""
        ep_dir = tmp_path / "ep"
        ep_dir.mkdir()
        (ep_dir / "work").mkdir()
        (ep_dir / "renders").mkdir()
        tl = self._make_timeline(ep_dir)

        with patch("avs.render.ffmpeg.ffmpeg_available", return_value=False):
            from avs.render.ffmpeg import render_rough_cut, RenderError
            with pytest.raises(RenderError, match="ffmpeg"):
                render_rough_cut(ep_dir, tl, force=True)


# ── 布局测试 ──────────────────────────────────────────────────────────────

class TestLayouts:
    def test_contain_filter_output(self):
        from avs.render.layouts import contain_filter
        f = contain_filter(1920, 1080)
        assert "1080" in f
        assert "1920" in f
        assert "pad" in f

    def test_cover_filter_output(self):
        from avs.render.layouts import cover_filter
        f = cover_filter(1920, 1080)
        assert "crop" in f

    def test_choose_layout_default_screen_focus_for_landscape(self):
        """Test landscape defaults to screen_focus (not contain)."""
        from avs.render.layouts import choose_layout
        f = choose_layout(None, 1920, 1080)  # 横屏
        assert "split[main][bg]" in f  # screen_focus 使用 split
        assert "boxblur" in f  # screen_focus 使用模糊背景

    def test_choose_layout_default_contain_for_portrait(self):
        """Test portrait defaults to contain."""
        from avs.render.layouts import choose_layout
        f = choose_layout(None, 1080, 1920)  # 竖屏
        assert "pad" in f  # contain 使用 pad

    def test_choose_layout_cover(self):
        from avs.render.layouts import choose_layout
        f = choose_layout({"layout": "cover"}, 1920, 1080)
        assert "crop" in f


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="ffmpeg 不可用")
def test_timeline_and_render_cli_state_sequence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path
    real_root = Path(__file__).resolve().parents[1]
    shutil.copytree(real_root / "config", root / "config")
    (root / "AGENTS.md").write_text("# test", encoding="utf-8")
    ep_dir = root / "episodes" / "active" / "EP-M6-CLI"
    ep_dir.mkdir(parents=True)
    create_episode_skeleton(ep_dir)
    content = ep_dir / "work" / "content"
    (content / "script.json").write_text(json.dumps({
        "segments": [{"segment_id": "seg001", "text": "模块六真实字幕"}],
    }), encoding="utf-8")
    (content / "storyboard.json").write_text(json.dumps({
        "shots": [{
            "scene_id": "scene001", "script_segment_ids": ["seg001"],
            "duration": 2.0, "visual_type": "placeholder", "asset_ids": [],
            "caption": "模块六真实字幕", "motion_template": None,
            "missing_assets": ["演示占位素材"], "notes": None,
        }],
    }), encoding="utf-8")
    (ep_dir / "work" / "asset-manifest.json").write_text(
        json.dumps({"assets": []}), encoding="utf-8",
    )
    model = EpisodeModel.create("EP-M6-CLI", mode="ORIGINAL")
    for status in ("INGESTED", "CONTENT_READY", "ASSETS_READY"):
        model.transition(status)
    for stage in ("ingest", "content", "assets"):
        model.complete_stage(stage)
    model.save(ep_dir / "episode.json")
    monkeypatch.setattr("avs.cli_timeline._find_project_root", lambda: root)
    runner = CliRunner()

    timeline = runner.invoke(main, ["timeline", "build", "EP-M6-CLI"])
    assert timeline.exit_code == 0, timeline.output
    assert EpisodeModel.load(ep_dir / "episode.json").status == "TIMELINE_READY"
    subtitles = runner.invoke(main, ["subtitles", "build", "EP-M6-CLI"])
    assert subtitles.exit_code == 0, subtitles.output
    render = runner.invoke(main, ["render", "rough", "EP-M6-CLI"])
    assert render.exit_code == 0, render.output
    assert EpisodeModel.load(ep_dir / "episode.json").status == "ROUGH_CUT_READY"
    assert (ep_dir / "renders" / "preview-clean.mp4").is_file()
    assert (ep_dir / "renders" / "preview-with-captions.mp4").is_file()


def test_module6_demo_requires_force_to_replace_existing_episode(tmp_path: Path) -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "create_module6_demo.py"
    spec = importlib.util.spec_from_file_location("create_module6_demo", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.create_demo(tmp_path)
    marker = tmp_path / "episodes" / "active" / "EP-M6-DEMO" / "input" / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError, match="--force"):
        module.create_demo(tmp_path)
    assert marker.read_text(encoding="utf-8") == "keep"
