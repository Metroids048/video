from avs.render.primitives.filters import build_visual_filter


def test_screenshot_full_never_builds_parallel_evidence_planes():
    graph = build_visual_filter("screenshot_full", width=1080, height=1920)
    forbidden = ("split=", "hstack=", "vstack=", "overlay=")
    assert not any(token in graph for token in forbidden)
