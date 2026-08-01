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
    """Test landscape detection."""
    assert is_landscape(1920, 1080) is True
    assert is_landscape(1280, 720) is True
    assert is_landscape(1080, 1920) is False
    assert is_landscape(1080, 1080) is False
    assert is_landscape(None, None) is False
    assert is_landscape(0, 0) is False


def test_contain_filter() -> None:
    """Test contain layout produces black padding."""
    result = contain_filter(1920, 1080)
    assert "scale=1080:1920" in result
    assert "force_original_aspect_ratio=decrease" in result
    assert "pad=1080:1920" in result
    assert "color=black" in result


def test_cover_filter() -> None:
    """Test cover layout crops to fill canvas."""
    result = cover_filter(1920, 1080)
    assert "scale=1080:1920" in result
    assert "force_original_aspect_ratio=increase" in result
    assert "crop=1080:1920" in result


def test_screen_focus_filter() -> None:
    """Test screen_focus layout for landscape recordings."""
    result = screen_focus_filter(1920, 1080)
    assert "split[main][bg]" in result
    assert "boxblur" in result
    assert "overlay=" in result
    # Should have background blur and main screen overlay


def test_screen_stack_filter() -> None:
    """Test screen_stack layout for landscape recordings."""
    result = screen_stack_filter(1920, 1080)
    assert "scale=1080:" in result
    assert "split[top][bottom]" in result
    assert "vstack" in result
    assert "crop=1080:1920" in result


def test_choose_layout_landscape_defaults_to_screen_focus() -> None:
    """Test landscape source defaults to screen_focus."""
    result = choose_layout(None, 1920, 1080)
    assert "split[main][bg]" in result
    assert "boxblur" in result


def test_choose_layout_portrait_defaults_to_contain() -> None:
    """Test portrait source defaults to contain."""
    result = choose_layout(None, 1080, 1920)
    assert "pad=1080:1920" in result
    assert "color=black" in result


def test_choose_layout_landscape_rejects_contain(caplog: pytest.LogCaptureFixture) -> None:
    """Test landscape with explicit contain logs warning and downgrades."""
    transform = {"layout": "contain"}
    result = choose_layout(transform, 1920, 1080)

    # Should downgrade to screen_focus
    assert "split[main][bg]" in result

    # Should log warning
    assert "不应使用 contain 布局" in caplog.text
    assert "降级为 screen_focus" in caplog.text


def test_choose_layout_landscape_explicit_screen_stack() -> None:
    """Test landscape with explicit screen_stack."""
    transform = {"layout": "screen_stack"}
    result = choose_layout(transform, 1920, 1080)
    assert "vstack" in result


def test_choose_layout_landscape_explicit_cover() -> None:
    """Test landscape with explicit cover."""
    transform = {"layout": "cover"}
    result = choose_layout(transform, 1920, 1080)
    assert "force_original_aspect_ratio=increase" in result
    assert "crop=1080:1920" in result


def test_choose_layout_portrait_explicit_cover() -> None:
    """Test portrait with explicit cover."""
    transform = {"layout": "cover"}
    result = choose_layout(transform, 1080, 1920)
    assert "force_original_aspect_ratio=increase" in result


def test_choose_layout_custom_default_strategy() -> None:
    """Test custom default landscape strategy."""
    result = choose_layout(None, 1920, 1080, default_landscape_strategy="screen_stack")
    assert "vstack" in result
