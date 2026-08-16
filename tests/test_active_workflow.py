"""Active multimodal workflow contracts."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from avs.active import active_analyze, active_final_render, active_preview
from avs.cli import main
from avs.ingest import run_ingest
from avs.models.episode import EpisodeModel
from avs.paths import create_episode_skeleton
from avs.render.primitives import PRIMITIVES, apply_redactions, primitive_filter
from avs.timeline.models import Clip, Timeline, Track
from avs.timeline.shot_expander import expand_shot
from avs.workflow import action_for_episode


def _png(path: Path) -> None:
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (320, 180), "white").save(path)


def test_ingest_writes_active_manifest_and_analyze_blocks_without_provider(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    ep_dir = tmp_path / "EP-ACTIVE"
    ep_dir.mkdir()
    create_episode_skeleton(ep_dir)
    model = EpisodeModel.create("EP-ACTIVE")
    model.save(ep_dir / "episode.json")
    _png(ep_dir / "input" / "images" / "product.png")
    (ep_dir / "input" / "product-spec.md").write_text("产品定位与模块边界", encoding="utf-8")

    run_ingest(ep_dir, model.id)
    model.transition("INGESTED")
    model.complete_stage("ingest")
    model.save(ep_dir / "episode.json")
    result = active_analyze(ep_dir, model)

    manifest = json.loads((ep_dir / "work" / "input-manifest.json").read_text(encoding="utf-8"))
    assert manifest["assets"][0]["must_use"] is True
    assert result["asset_intelligence"]["blocked"] is True
    reloaded = EpisodeModel.load(ep_dir / "episode.json")
    assert reloaded.to_dict()["blocked"] is True
    assert action_for_episode(ep_dir, reloaded).stage == "analyze"


def test_analyze_retries_blocked_provider_result_with_force(tmp_path: Path) -> None:
    ep_dir = tmp_path / "EP-RETRY"
    ep_dir.mkdir()
    create_episode_skeleton(ep_dir)
    (ep_dir / "work" / "input-manifest.json").write_text(
        json.dumps({"episode_id": "EP-RETRY", "assets": []}), encoding="utf-8"
    )
    model = EpisodeModel.create("EP-RETRY")
    model.transition("INGESTED")
    model.complete_stage("ingest")
    model.save(ep_dir / "episode.json")
    blocked_intelligence = {
        "blocked": True,
        "blocking_reason": "缺 Provider",
        "provider": "none",
        "assets": [],
    }
    ready_intelligence = {**blocked_intelligence, "blocked": False, "blocking_reason": None, "provider": "openai"}
    ready = {"blocked": False}

    with (
        patch("avs.active.analyze_assets", return_value=blocked_intelligence) as analyze_assets,
        patch("avs.active.analyze_recordings", return_value={}),
        patch("avs.active.analyze_documents", return_value=ready),
        patch("avs.active.transcribe_audio_assets", return_value=ready),
    ):
        active_analyze(ep_dir, model)

    paused = EpisodeModel.load(ep_dir / "episode.json")
    assert analyze_assets.call_args.kwargs["force"] is False
    assert "analyze" not in paused.completed_stages
    assert paused.blocked_stage == "analyze"

    with (
        patch("avs.active.analyze_assets", return_value=ready_intelligence) as analyze_assets,
        patch("avs.active.analyze_recordings", return_value={}),
        patch("avs.active.analyze_documents", return_value=ready),
        patch("avs.active.transcribe_audio_assets", return_value=ready),
    ):
        active_analyze(ep_dir, paused)

    resumed = EpisodeModel.load(ep_dir / "episode.json")
    assert analyze_assets.call_args.kwargs["force"] is True
    assert "analyze" in resumed.completed_stages
    assert resumed.blocked is False
    assert resumed.blocked_stage is None


def _visual_review_episode(tmp_path: Path, episode_id: str) -> tuple[Path, EpisodeModel]:
    ep_dir = tmp_path / episode_id
    ep_dir.mkdir()
    create_episode_skeleton(ep_dir)
    for relative in (
        "work/content/script.json",
        "work/content/evidence-map.json",
        "work/content/shot-plan.json",
        "work/content/reference-selection.json",
        "work/analysis/asset-intelligence.json",
    ):
        path = ep_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    model = EpisodeModel.create(episode_id)
    for status in ("INGESTED", "CONTENT_READY", "ASSETS_READY", "TIMELINE_READY"):
        model.transition(status)
    model.save(ep_dir / "episode.json")
    return ep_dir, model


def test_visual_review_provider_block_is_not_completed_and_retries(tmp_path: Path, monkeypatch) -> None:
    ep_dir, model = _visual_review_episode(tmp_path, "EP-VISION")
    provider_blocked = {
        "passed": False,
        "blocked": True,
        "failures": [{"failure_code": "VISION_PROVIDER_UNAVAILABLE"}],
    }
    monkeypatch.setattr("avs.cli_active._episode", lambda _episode_id: (ep_dir, model))

    with patch("avs.qa.visual_reviewer.review_video", return_value=provider_blocked):
        result = CliRunner().invoke(main, ["visual-review", "EP-VISION"])

    paused = EpisodeModel.load(ep_dir / "episode.json")
    assert result.exit_code == 2, result.output
    assert "visual-review" not in paused.completed_stages
    assert paused.blocked_stage == "visual-review"
    assert action_for_episode(ep_dir, paused).command == ("visual-review",)

    passed = {"passed": True, "blocked": False, "failures": []}
    monkeypatch.setattr("avs.cli_active._episode", lambda _episode_id: (ep_dir, paused))
    with patch("avs.qa.visual_reviewer.review_video", return_value=passed) as review_video:
        result = CliRunner().invoke(main, ["visual-review", "EP-VISION"])

    resumed = EpisodeModel.load(ep_dir / "episode.json")
    assert result.exit_code == 0, result.output
    assert review_video.call_args.kwargs["force"] is True
    assert "visual-review" in resumed.completed_stages
    assert resumed.blocked_stage is None


def test_visual_review_semantic_failure_requires_human_reset(tmp_path: Path, monkeypatch) -> None:
    ep_dir, model = _visual_review_episode(tmp_path, "EP-SEMANTIC")
    semantic_failure = {
        "passed": False,
        "blocked": True,
        "failures": [{"failure_code": "SEMANTIC_MISMATCH"}],
    }
    monkeypatch.setattr("avs.cli_active._episode", lambda _episode_id: (ep_dir, model))

    def write_semantic_failure(*args, **kwargs):
        report_path = ep_dir / "work" / "qa" / "visual-review.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(semantic_failure), encoding="utf-8")
        return semantic_failure

    with patch("avs.qa.visual_reviewer.review_video", side_effect=write_semantic_failure):
        result = CliRunner().invoke(main, ["visual-review", "EP-SEMANTIC"])

    paused = EpisodeModel.load(ep_dir / "episode.json")
    action = action_for_episode(ep_dir, paused)
    assert result.exit_code == 2, result.output
    assert "visual-review" not in paused.completed_stages
    assert action.kind == "human"
    assert action.command is None
    assert "CONTENT_READY" in action.summary


def test_screenshot_intro_uses_explicit_notes_for_preview_but_marks_provider_review_pending(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    ep_dir = tmp_path / "EP-SCREENSHOT"
    ep_dir.mkdir()
    create_episode_skeleton(ep_dir)
    model = EpisodeModel.create("EP-SCREENSHOT", input_mode="screenshot_intro")
    model.save(ep_dir / "episode.json")
    _png(ep_dir / "input" / "images" / "product.png")
    (ep_dir / "input" / "product-spec.md").write_text("产品定位与模块边界", encoding="utf-8")
    (ep_dir / "input" / "input-manifest.json").write_text(json.dumps({
        "assets": [{
            "asset_id": "product",
            "source_path": "input/images/product.png",
            "must_use": True,
            "user_note": "研究入口；策略库；回测验证",
        }, {
            "asset_id": "product-spec",
            "source_path": "input/product-spec.md",
            "must_use": True,
            "user_note": "产品定位与模块边界",
        }]
    }, ensure_ascii=False), encoding="utf-8")

    run_ingest(ep_dir, model.id)
    model.transition("INGESTED")
    model.complete_stage("ingest")
    model.save(ep_dir / "episode.json")
    result = active_analyze(ep_dir, model)

    assert result["asset_intelligence"]["blocked"] is False
    assert result["asset_intelligence"]["provider"] == "manual"
    assert result["asset_intelligence"]["requires_provider_review"] is True
    assert result["asset_intelligence"]["assets"][0]["visible_facts"] == ["研究入口", "策略库", "回测验证"]
    assert EpisodeModel.load(ep_dir / "episode.json").status == "INGESTED"


def test_three_assets_expand_to_three_atomic_shots() -> None:
    shots, exclusions = expand_shot({
        "shot_id": "shot-001", "duration_seconds": 3.0,
        "asset_refs": [{"asset_id": "a"}, {"asset_id": "b"}, {"asset_id": "c"}],
    })
    assert [shot["asset_refs"][0]["asset_id"] for shot in shots] == ["a", "b", "c"]
    assert exclusions == []


def test_all_required_primitives_have_filter_graphs() -> None:
    assert len(PRIMITIVES) >= 15
    graphs = {
        primitive: primitive_filter(primitive, duration=2.0)
        for primitive in PRIMITIVES
    }
    assert all("format=yuv420p" in graph for graph in graphs.values())
    assert len(set(graphs.values())) == len(PRIMITIVES)


def test_focus_primitive_uses_normalized_roi() -> None:
    graph = primitive_filter(
        "screenshot_focus", duration=2.0, region=[0.25, 0.2, 0.5, 0.4]
    )
    assert "crop=iw*0.5:ih*0.4:iw*0.25:ih*0.2" in graph


def test_redactions_are_burned_after_the_primitive_layout() -> None:
    graph = apply_redactions(
        primitive_filter("screenshot_focus", duration=2.0),
        [[0.1, 0.2, 0.3, 0.15]],
    )
    assert "drawbox=x=iw*0.1:y=ih*0.2:w=iw*0.3:h=ih*0.15:color=black@1:t=fill" in graph
    assert graph.endswith("format=yuv420p")


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg 不可用")
@pytest.mark.parametrize("primitive", sorted(PRIMITIVES))
def test_every_primitive_filter_executes_in_ffmpeg(primitive: str) -> None:
    graph = primitive_filter(
        primitive, duration=0.2, width=270, height=480, fps=10,
        region=[0.2, 0.2, 0.6, 0.5],
    )
    result = subprocess.run([
        "ffmpeg", "-v", "error", "-f", "lavfi", "-i",
        "testsrc2=size=640x360:rate=10:duration=0.2", "-vf", graph,
        "-frames:v", "2", "-f", "null", "-",
    ], capture_output=True, text=True, timeout=20, check=False)
    assert result.returncode == 0, result.stderr


def _active_content(ep_dir: Path) -> None:
    content = ep_dir / "work" / "content"
    content.mkdir(parents=True)
    (content / "creative-brief.json").write_text("{}", encoding="utf-8")
    (content / "script.json").write_text(json.dumps({
        "segments": [{"segment_id": "seg-1", "spoken_text": "开场"}],
    }), encoding="utf-8")
    (content / "shot-plan.json").write_text(json.dumps({
        "shots": [{
            "shot_id": "shot-1", "segment_id": "seg-1", "duration_seconds": 2.0,
            "primitive": "kinetic_text", "asset_refs": [], "reference_pattern_ids": [],
            "keyframes": [],
        }],
    }), encoding="utf-8")


def test_active_preview_runs_hyperframes_on_formal_path(tmp_path: Path) -> None:
    ep_dir = tmp_path / "episodes" / "active" / "EP-ACTIVE"
    _active_content(ep_dir)
    timeline = Timeline("EP-ACTIVE", total_duration=2.0, tracks=[Track(
        track_id="voice", kind="audio", audio_role="voice",
        clips=[Clip(clip_id="locked-voice", start=0.0, duration=2.0, asset_ref="work/narration.mp3")],
    )])
    words = ep_dir / "work" / "final-narration.words.json"
    words.parent.mkdir(parents=True, exist_ok=True)
    words.write_text(json.dumps({"words": [{"text": "开场", "start": 0.0, "end": 1.0, "confidence": 1.0}]}), encoding="utf-8")
    model = MagicMock(id="EP-ACTIVE", status="CONTENT_READY")
    with (
        patch("avs.active.build_timeline", return_value=timeline),
        patch("avs.render.render_rough_cut", return_value={}),
        patch("avs.hyperframes.render_motion_graphics", return_value=SimpleNamespace(output_path=None)) as motion,
    ):
        active_preview(ep_dir, model, force=True)

    motion.assert_called_once()
    storyboard = json.loads((ep_dir / "work" / "content" / "storyboard.json").read_text(encoding="utf-8"))
    assert storyboard["shots"][0]["motion_template"] == "HookTitle"


def test_active_final_render_creates_distinct_clean_and_captioned_outputs(tmp_path: Path) -> None:
    ep_dir = tmp_path / "episodes" / "active" / "EP-ACTIVE"
    (ep_dir / "work" / "qa").mkdir(parents=True)
    (ep_dir / "renders").mkdir()
    (ep_dir / "work" / "qa" / "visual-review.json").write_text(
        json.dumps({"passed": True, "blocked": False}), encoding="utf-8"
    )
    timeline = Timeline("EP-ACTIVE", total_duration=2.0)
    timeline.save(ep_dir / "work" / "timeline.json")
    preview_clean = ep_dir / "renders" / "preview-clean.mp4"
    preview_captions = ep_dir / "renders" / "preview-with-captions.mp4"
    preview_clean.write_bytes(b"clean")
    preview_captions.write_bytes(b"captions")
    model = MagicMock(id="EP-ACTIVE", status="TIMELINE_READY")

    def fake_motion(_root, _episode, _timeline, **kwargs):
        output = kwargs["output_path"]
        output.write_bytes(b"motion-" + kwargs["base_video"].read_bytes())
        return SimpleNamespace(output_path=output)

    with (
        patch("avs.active.build_srt"),
        patch("avs.render.render_rough_cut", return_value={
            "preview_clean": preview_clean,
            "preview_with_captions": preview_captions,
        }),
        patch("avs.hyperframes.render_motion_graphics", side_effect=fake_motion) as motion,
    ):
        result = active_final_render(ep_dir, model, force=True)

    assert motion.call_count == 2
    assert result["final_clean"].read_bytes() == b"motion-clean"
    assert result["final_with_captions"].read_bytes() == b"motion-captions"
    assert result["final_clean"] != preview_clean
