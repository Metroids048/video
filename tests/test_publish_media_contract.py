from pathlib import Path

from avs.qa.audio_levels import audio_is_publishable
from avs.render.primitives.filters import build_visual_filter


def test_publish_audio_rejects_missing_or_inaudible_track():
    assert audio_is_publishable(has_audio=False, mean_db=-16.0, max_db=-1.5) is False
    assert audio_is_publishable(has_audio=True, mean_db=-80.0, max_db=-50.0) is False


def test_publish_audio_accepts_audible_track():
    assert audio_is_publishable(has_audio=True, mean_db=-18.0, max_db=-2.0) is True


def test_screen_focus_is_single_panel_not_split_or_fake_compare():
    filtergraph = build_visual_filter("screenshot_full", width=1080, height=1920)
    assert "split=" not in filtergraph
    assert "hstack=" not in filtergraph
    assert "vstack=" not in filtergraph
    assert "crop=1080:1920" not in filtergraph
