"""Tests for layout strategies and full-frame landscape safety."""
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


def test_contain_filter_preserves_full_frame() -> None:
    result = contain_filter(1920, 1080)
    assert "scale=1080:1920" in result
    assert "force_original_aspect_ratio=decrease" in result
    assert "pad=1080:1920" in result
    assert "crop=1080:1920" not in result


def test_cover_filter_is_explicitly_destructive() -> None:
    result = cover_filter(1920, 1080)
    assert "force_original_aspect_ratio=increase" in result
    assert "crop=1080:1920" in result


def test_screen_focus_filter_is_explicitly_destructive_roi_crop() -> None:
    result = screen_focus_filter(1920, 1080)
    assert "scale=-2:1920" in result
    assert "crop=1080:1920" in result
    assert "split[main][bg]" not in result
    assert "boxblur" not in result
    assert "overlay=" not in result
    assert "vstack" not in result


def test_screen_stack_filter() -> None:
    result = screen_stack_filter(1920, 1080)
    assert "vstack" in result
    assert "crop=1080:1920" in result


def test_landscape_defaults_to_full_frame_contain_not_crop() -> None:
    result = choose_layout(None, 1920, 1080)
    assert "force_original_aspect_ratio=decrease" in result
    assert "pad=1080:1920" in result
    assert "crop=1080:1920" not in result
    assert "scale=-2:1920" not in result


def test_explicit_landscape_contain_is_preserved_not_downgraded(caplog: pytest.LogCaptureFixture) -> None:
    result = choose_layout({"layout": "contain"}, 1920, 1080)

    assert "force_original_aspect_ratio=decrease" in result
    assert "pad=1080:1920" in result
    assert "crop=1080:1920" not in result
    assert "不应使用 contain" not in caplog.text


def test_landscape_screen_focus_without_crop_authorization_falls_back_to_full_frame(
    caplog: pytest.LogCaptureFixture,
) -> None:
    result = choose_layout({"layout": "screen_focus", "focus_x": 0.8}, 1920, 1080)

    assert "force_original_aspect_ratio=decrease" in result
    assert "pad=1080:1920" in result
    assert "crop=1080:1920" not in result
    assert "destructive crop" in caplog.text


def test_landscape_screen_focus_requires_explicit_crop_authorization() -> None:
    result = choose_layout(
        {"layout": "screen_focus", "focus_x": 0.8, "allow_destructive_crop": True},
        1920,
        1080,
    )

    assert "scale=-2:1920" in result
    assert "crop=1080:1920" in result


def test_landscape_cover_without_crop_authorization_falls_back_to_full_frame() -> None:
    result = choose_layout({"layout": "cover"}, 1920, 1080)

    assert "force_original_aspect_ratio=decrease" in result
    assert "crop=1080:1920" not in result


def test_landscape_cover_requires_explicit_crop_authorization() -> None:
    result = choose_layout(
        {"layout": "cover", "allow_destructive_crop": True},
        1920,
        1080,
    )

    assert "force_original_aspect_ratio=increase" in result
    assert "crop=1080:1920" in result


def test_choose_layout_portrait_defaults_to_contain() -> None:
    result = choose_layout(None, 1080, 1920)
    assert "pad=1080:1920" in result


def test_custom_landscape_strategy_cannot_bypass_full_frame_safety_without_authorization() -> None:
    result = choose_layout(None, 1920, 1080, default_landscape_strategy="screen_stack")
    assert "force_original_aspect_ratio=decrease" in result
    assert "crop=1080:1920" not in result
