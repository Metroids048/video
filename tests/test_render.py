"""tests/test_render.py — 模块6 渲染单元测试（FFmpeg 可选）。"""
from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from avs.timeline.models import Canvas, Clip, Timeline, Track
from avs.render.captions import build_srt, _seconds_to_srt_time, has_subtitle_overflow
from avs.render.audio import ffmpeg_available


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

    def test_render_idempotent(self, tmp_path):
        """已存在且 force=False 时直接返回，不重新渲染。"""
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
        # 应返回已有文件（内容未变）
        assert result["preview_clean"].read_bytes() == b"fake"

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

    def test_choose_layout_default_contain(self):
        from avs.render.layouts import choose_layout
        f = choose_layout(None, 1920, 1080)
        assert "pad" in f  # contain 使用 pad

    def test_choose_layout_cover(self):
        from avs.render.layouts import choose_layout
        f = choose_layout({"layout": "cover"}, 1920, 1080)
        assert "crop" in f
