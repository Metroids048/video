from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from avs.render.ffmpeg import _caption_filter
from avs.render.primitives import primitive_filter


ROOT = Path(__file__).resolve().parents[1]


def test_caption_filter_uses_explicit_portrait_playres_and_safe_zone(tmp_path: Path) -> None:
    graph = _caption_filter(tmp_path / "captions.srt")

    assert "original_size=1080x1920" in graph
    assert "FontSize=50" in graph
    assert "MarginV=260" in graph
    assert "Alignment=2" in graph


def test_screenshot_full_preserves_wide_screen_evidence() -> None:
    graph = primitive_filter("screenshot_full", duration=3.0)

    assert "force_original_aspect_ratio=decrease" in graph
    assert "pad=1080:1920" in graph
    assert "force_original_aspect_ratio=increase" not in graph


def test_ep01_visual_review_cannot_self_approve_without_external_review(tmp_path: Path) -> None:
    episode = tmp_path / "EP-QUALITY-REGRESSION"
    (episode / "work" / "qa").mkdir(parents=True)

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "mark_ep01_visual_review.py"), str(episode)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert not (episode / "work" / "qa" / "visual-review.json").exists()
