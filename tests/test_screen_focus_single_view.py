from avs.render.layouts import choose_layout, screen_focus_filter


def test_screen_focus_is_one_explicit_destructive_viewport_not_blur_plus_inset():
    graph = screen_focus_filter(2556, 1286)
    for forbidden in ("split", "overlay", "boxblur"):
        assert forbidden not in graph
    assert "crop=1080:1920" in graph
    assert "scale=-2:1920" in graph


def test_authorized_screen_focus_accepts_semantic_horizontal_focus():
    left = choose_layout(
        {"layout": "screen_focus", "focus_x": 0.2, "allow_destructive_crop": True},
        2556,
        1286,
    )
    right = choose_layout(
        {"layout": "screen_focus", "focus_x": 0.8, "allow_destructive_crop": True},
        2556,
        1286,
    )
    assert left != right
    assert "crop=1080:1920" in left
    assert "crop=1080:1920" in right


def test_unauthorized_screen_focus_falls_back_to_full_frame():
    graph = choose_layout({"layout": "screen_focus", "focus_x": 0.8}, 2556, 1286)
    assert "force_original_aspect_ratio=decrease" in graph
    assert "crop=1080:1920" not in graph
