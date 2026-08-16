"""Tests for layout strategies (screen_focus, screen_stack, contain, cover)."""
from __future__ import annotations

import pytest

from avs.render.layouts import (
    choose_layout,
    contain_filter,
    cover_filter,
    is_landscape,
    screen_focus_filter,
    screen_stack_filter,
)


def test_is_landscape() -> None:
    assert is_landscape(1920, 1080) is True
    assert is_landscape(1280, 720) is True
    assert is_landscape(1080, 1920) is False
    assert is_landscape(1080, 1080) is False
    assert is_landscape(None, None) is False
    assert is_landscape(0, 0) is False


def test_contain_filter() -> None:
    result = contain_filter(1920, 1080)
    assert "scale=1080:1920" in result
    assert "force_original_aspect_ratio=decrease" in result
    assert "pad=1080:1920" in result
    assert "color=black" in result


def test_cover_filter() -> None:
    result = cover_filter(1920, 1080)
    assert "scale=1080:1920" in result
    assert "force_original_aspect_ratio=increase" in result
    assert "crop=1080:1920" in result


def test_screen_focus_filter_is_single_full_height_view_not_split_panel() -> None:
    result = screen_focus_filter(1920, 1080)
    assert "scale=-2:1920" in result
    assert "crop=1080:1920" in result
    assert "split[main][bg]" not in result
    assert "boxblur" not in result
    assert "overlay=" not in result
    assert "vstack" not in result


def test_screen_stack_filter() -> None:
    result = screen_stack_filter(1920, 1080)
    assert "scale=1080:" in result
    assert "split[top][bottom]" in result
    assert "vstack" in result
    assert "crop=1080:1920" in result


def test_choose_layout_landscape_defaults_to_single_screen_focus() -> None:
    result = choose_layout(None, 1920, 1080)
    assert "scale=-2:1920" in result
    assert "crop=1080:1920" in result
    assert "split[main][bg]" not in result
    assert "boxblur" not in result


def test_choose_layout_portrait_defaults_to_contain() -> None:
    result = choose_layout(None, 1080, 1920)
    assert "pad=1080:1920" in result
    assert "color=black" in result


def test_choose_layout_landscape_rejects_contain(caplog: pytest.LogCaptureFixture) -> None:
    transform = {"layout": "contain"}
    result = choose_layout(transform, 1920, 1080)

    assert "scale=-2:1920" in result
    assert "crop=1080:1920" in result
    assert "split[main][bg]" not in result
    assert "不应使用 contain 布局" in caplog.text
    assert "降级为 screen_focus" in caplog.text


def test_choose_layout_landscape_explicit_screen_stack() -> None:
    transform = {"layout": "screen_stack"}
    result = choose_layout(transform, 1920, 1080)
    assert "vstack" in result


def test_choose_layout_landscape_explicit_cover() -> None:
    transform = {"layout": "cover"}
    result = choose_layout(transform, 1920, 1080)
    assert "force_original_aspect_ratio=increase" in result
    assert "crop=1080:1920" in result


def test_choose_layout_portrait_explicit_cover() -> None:
    transform = {"layout": "cover"}
    result = choose_layout(transform, 1080, 1920)
    assert "force_original_aspect_ratio=increase" in result


def test_choose_layout_custom_default_strategy() -> None:
    result = choose_layout(None, 1920, 1080, default_landscape_strategy="screen_stack")
    assert "vstack" in result
