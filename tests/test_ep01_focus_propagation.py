from pathlib import Path


def test_ep01_timeline_defaults_to_full_frame_not_screen_focus_crop():
    source = (Path(__file__).resolve().parents[1] / "scripts" / "build_ep01_timeline.py").read_text(encoding="utf-8")
    assert '"layout": "fit_full_frame"' in source
    assert '"layout": "screen_focus"' not in source
    assert '"focus_x"' not in source
    assert '"allow_destructive_crop"' not in source
