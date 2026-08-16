from pathlib import Path


def test_ep01_timeline_propagates_scene_focus_x():
    source = (Path(__file__).resolve().parents[1] / "scripts" / "build_ep01_timeline.py").read_text(encoding="utf-8")
    assert '"focus_x": float(shot.get("focus_x", 0.5))' in source
