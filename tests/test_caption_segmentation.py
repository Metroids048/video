"""Tests for semantic caption segmentation."""
from __future__ import annotations

import pytest

from avs.render.caption_segmentation import (
    CaptionCue,
    check_caption_quality,
    format_cue_lines,
    segment_caption,
)


def test_caption_cue_char_count() -> None:
    """Test CJK character counting."""
    cue = CaptionCue(0.0, 2.0, "这是一个测试。")
    assert cue.char_count == 6
    assert cue.duration == 2.0


def test_segment_caption_short_text() -> None:
    """Test short text remains as single cue."""
    cues = segment_caption("这是测试", 0.0, 2.0)
    assert len(cues) == 1
    assert cues[0].text == "这是测试"
    assert cues[0].start == 0.0
    assert cues[0].end == 2.0


def test_segment_caption_long_text_with_punctuation() -> None:
    """Test long text is segmented by punctuation."""
    text = "这是第一句。这是第二句，内容较长。这是第三句！"
    cues = segment_caption(text, 0.0, 10.0, max_chars_per_cue=12)

    assert len(cues) >= 2
    # Each cue should respect max chars
    for cue in cues:
        assert cue.char_count <= 14  # Allow some margin


def test_segment_caption_respects_min_duration() -> None:
    """Test cues respect minimum duration."""
    text = "短句。"
    cues = segment_caption(text, 0.0, 2.0, min_cue_seconds=0.8)

    for cue in cues:
        assert cue.duration >= 0.8 or abs(cue.duration - 0.8) < 0.1


def test_segment_caption_distributes_time() -> None:
    """Test time distribution across cues."""
    text = "第一部分内容较长。第二部分也很长。"
    cues = segment_caption(text, 0.0, 6.0, max_chars_per_cue=10)

    total_duration = sum(cue.duration for cue in cues)
    assert abs(total_duration - 6.0) < 0.1


def test_format_cue_lines_single_line() -> None:
    """Test short text stays on single line."""
    result = format_cue_lines("这是测试", max_chars_per_line=14)
    assert "\n" not in result
    assert result == "这是测试"


def test_format_cue_lines_splits_long_text() -> None:
    """Test long text is split into multiple lines."""
    text = "这是一个很长的测试文本需要分行显示"
    result = format_cue_lines(text, max_chars_per_line=14, max_lines=2)

    lines = result.split("\n")
    assert len(lines) <= 2
    for line in lines:
        # Allow overflow indicator
        char_count = len([c for c in line.replace("...", "") if "一" <= c <= "鿿"])
        assert char_count <= 15


def test_format_cue_lines_respects_max_lines() -> None:
    """Test max lines constraint."""
    text = "第一句。第二句。第三句。第四句。"
    result = format_cue_lines(text, max_chars_per_line=6, max_lines=2)

    lines = result.split("\n")
    assert len(lines) <= 2


def test_check_caption_quality_good() -> None:
    """Test good quality caption passes checks."""
    cue = CaptionCue(0.0, 2.0, "这是正常速度的字幕")
    issues = check_caption_quality(cue, max_cjk_per_second=12.0)
    assert len(issues) == 0


def test_check_caption_quality_too_fast() -> None:
    """Test reading speed check."""
    cue = CaptionCue(0.0, 1.0, "这是一个非常长的字幕文本超过了推荐阅读速度")
    issues = check_caption_quality(cue, max_cjk_per_second=12.0)

    assert len(issues) > 0
    assert any("阅读速度过快" in issue for issue in issues)


def test_check_caption_quality_too_short() -> None:
    """Test duration too short."""
    cue = CaptionCue(0.0, 0.5, "短")
    issues = check_caption_quality(cue)

    assert any("时长过短" in issue for issue in issues)


def test_check_caption_quality_too_long() -> None:
    """Test duration too long."""
    cue = CaptionCue(0.0, 4.0, "这是一个很长的字幕")
    issues = check_caption_quality(cue)

    assert any("时长过长" in issue for issue in issues)


def test_check_caption_quality_too_many_chars() -> None:
    """Test too many characters."""
    cue = CaptionCue(0.0, 3.0, "这是一个包含超过二十四个中文字符的超长字幕文本内容")
    issues = check_caption_quality(cue)

    assert any("字符数过多" in issue for issue in issues)


def test_segment_caption_no_punctuation() -> None:
    """Test segmentation without punctuation."""
    text = "这是一个没有标点符号的很长文本需要强制切分"
    cues = segment_caption(text, 0.0, 5.0, max_chars_per_cue=12)

    assert len(cues) >= 2
    for cue in cues:
        assert cue.char_count <= 14


def test_segment_caption_empty_text() -> None:
    """Test empty text returns empty list."""
    cues = segment_caption("", 0.0, 2.0)
    assert len(cues) == 0


def test_format_cue_lines_empty_text() -> None:
    """Test empty text returns empty string."""
    result = format_cue_lines("")
    assert result == ""
