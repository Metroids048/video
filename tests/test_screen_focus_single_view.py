from avs.render.layouts import choose_layout, screen_focus_filter


def test_screen_focus_is_one_full_height_viewport_not_blur_plus_inset():
    graph = screen_focus_filter(2556, 1286)
    for forbidden in ("split", "overlay", "boxblur"):
        assert forbidden not in graph
    assert "crop=1080:1920" in graph
    assert "scale=-2:1920" in graph


def test_screen_focus_accepts_semantic_horizontal_focus():
    left = choose_layout({"layout": "screen_focus", "focus_x": 0.2}, 2556, 1286)
    right = choose_layout({"layout": "screen_focus", "focus_x": 0.8}, 2556, 1286)
    assert left != right
    assert "crop=1080:1920" in left
    assert "crop=1080:1920" in right
