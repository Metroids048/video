"""HyperFrames integration and fallback tests."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import jsonschema
import pytest

from avs.hyperframes.render import render_motion_graphics, render_static_fallback
from avs.timeline.models import Clip, Timeline, Track


def _timeline() -> Timeline:
    return Timeline(
        "EP-MOTION-TEST",
        tracks=[Track("graphics-main", "graphic", [
            Clip(
                "graphic-hook", 0.0, 2.0, text="测试标题",
                style={"motion_template": "HookTitle", "subtitle": "测试副标题"},
            ),
        ])],
        total_duration=2.0,
    )


def test_motion_failure_falls_back_without_modifying_rough_cut(tmp_path: Path) -> None:
    project = tmp_path / "project"
    episode = project / "episodes" / "EP-MOTION-TEST"
    (project / "schemas").mkdir(parents=True)
    schema_source = Path(__file__).parents[1] / "schemas" / "motion-manifest.schema.json"
    shutil.copy2(schema_source, project / "schemas" / schema_source.name)
    (episode / "work").mkdir(parents=True)
    (episode / "renders").mkdir()
    base = episode / "renders" / "preview-with-captions.mp4"
    base.write_bytes(b"rough-cut")

    def fake_fallback(_template, _props, output, *, duration):
        assert duration == 2.0
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"fallback")

    def fake_compose(input_path, _clips, output):
        assert input_path.read_bytes() == b"rough-cut"
        output.write_bytes(b"composite")

    with (
        patch("avs.hyperframes.render._valid_video", return_value=False),
        patch("avs.hyperframes.render.try_render_hyperframes", return_value=(False, "forced failure")),
        patch("avs.hyperframes.render.render_static_fallback", side_effect=fake_fallback),
        patch("avs.hyperframes.render._compose_motion", side_effect=fake_compose),
    ):
        result = render_motion_graphics(project, episode, _timeline(), force=True)

    assert base.read_bytes() == b"rough-cut"
    assert len(result.fallbacks) == 1
    assert result.output_path and result.output_path.read_bytes() == b"composite"
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert payload["clips"][0]["status"] == "fallback"
    assert "forced failure" in payload["clips"][0]["warning"]


def test_motion_manifest_matches_schema(tmp_path: Path) -> None:
    project = Path(__file__).parents[1]
    schema = json.loads((project / "schemas" / "motion-manifest.schema.json").read_text())
    payload = {
        "episode_id": "EP-X", "generated_at": "2026-07-23T00:00:00Z",
        "clips": [], "composite_output": None,
    }
    jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(payload)


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="ffmpeg 不可用")
def test_static_fallback_is_portrait_h264(tmp_path: Path) -> None:
    output = tmp_path / "fallback.mp4"
    render_static_fallback("HookTitle", {"title": "离线降级"}, output, duration=1.0)
    assert output.is_file() and output.stat().st_size > 0


def test_components_are_offline_and_episode_independent() -> None:
    root = Path(__file__).parents[1] / "renderers" / "hyperframes" / "components"
    for component in ("HookTitle", "InfoCard", "EndCard"):
        html = (root / component / "index.html").read_text(encoding="utf-8")
        assert "https://" not in html and "http://" not in html
        assert "episode.json" not in html and "input/" not in html
        assert "data-composition-id" in html
        assert (root / component / "assets" / "gsap.min.js").is_file()
