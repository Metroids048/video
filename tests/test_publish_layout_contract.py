from avs.render.primitives.filters import primitive_filter


def test_screenshot_full_never_builds_parallel_evidence_planes():
    graph = primitive_filter("screenshot_full", duration=3.0, width=1080, height=1920)
    forbidden = ("split=", "hstack=", "vstack=", "overlay=")
    assert not any(token in graph for token in forbidden)
    assert "force_original_aspect_ratio=decrease" in graph
