from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner

from avs.cli import main
from avs.content.schema import ContentValidationError, validate_content_bundle, validate_script
from avs.ingest.manifest import save_manifest
from avs.models.episode import EpisodeModel
from avs.paths import create_episode_skeleton


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


@pytest.fixture()
def content_episode(tmp_path: Path) -> Path:
    ep_dir = tmp_path / "episodes" / "active" / "EP-CONTENT"
    ep_dir.mkdir(parents=True)
    create_episode_skeleton(ep_dir)
    idea = ep_dir / "input" / "idea.md"
    idea.write_text("只陈述这个本地示例，不包含外部事实。", encoding="utf-8")
    prepared = ep_dir / "work" / "prepared" / "images" / "proof.png"
    prepared.parent.mkdir(parents=True)
    prepared.write_bytes(b"fixture")
    save_manifest(ep_dir, "EP-CONTENT", [{
        "asset_id": "asset-proof",
        "source_path": "input/images/proof.png",
        "working_path": "work/prepared/images/proof.png",
        "kind": "image",
        "mime_type": "image/png",
        "sha256": "a" * 64,
        "status": "ok",
    }])
    content = ep_dir / "work" / "content"
    content.mkdir(parents=True, exist_ok=True)
    script = {
        "episode_id": "EP-CONTENT",
        "total_duration_estimate": 5.0,
        "segments": [{
            "segment_id": "seg001",
            "text": "这是用户提供的本地示例。",
            "purpose": "hook",
            "target_duration": 5.0,
            "visual_hint": "展示用户图片",
            "source_refs": ["input/idea.md"],
            "status": "draft",
            "notes": None,
        }],
        "generated_at": _now(),
    }
    storyboard = {
        "episode_id": "EP-CONTENT",
        "shots": [{
            "scene_id": "scene001",
            "script_segment_ids": ["seg001"],
            "duration": 5.0,
            "visual_type": "image",
            "asset_ids": ["asset-proof"],
            "caption": "这是用户提供的本地示例。",
            "motion_template": None,
            "missing_assets": [],
            "notes": "contain",
        }],
        "asset_gaps": [],
        "generated_at": _now(),
    }
    (content / "script.json").write_text(json.dumps(script), encoding="utf-8")
    (content / "storyboard.json").write_text(json.dumps(storyboard), encoding="utf-8")
    (content / "brief.md").write_text("# Brief\n", encoding="utf-8")
    (content / "script.md").write_text("# Script\n", encoding="utf-8")
    (content / "storyboard.md").write_text("# Storyboard\n", encoding="utf-8")
    (content / "missing-assets.md").write_text("# Missing Assets\n\nNone.\n", encoding="utf-8")
    return ep_dir


def test_valid_content_bundle(content_episode: Path) -> None:
    validate_content_bundle(content_episode)


def test_missing_source_ref_rejected(content_episode: Path) -> None:
    script_path = content_episode / "work" / "content" / "script.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))
    script["segments"][0]["source_refs"] = ["input/not-found.md"]
    script_path.write_text(json.dumps(script), encoding="utf-8")
    with pytest.raises(ContentValidationError, match="source_ref"):
        validate_content_bundle(content_episode)


def test_unknown_script_segment_rejected(content_episode: Path) -> None:
    path = content_episode / "work" / "content" / "storyboard.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["shots"][0]["script_segment_ids"] = ["missing"]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ContentValidationError, match="Script Segment"):
        validate_content_bundle(content_episode)


def test_unknown_asset_rejected(content_episode: Path) -> None:
    path = content_episode / "work" / "content" / "storyboard.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["shots"][0]["asset_ids"] = ["not-in-manifest"]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ContentValidationError, match="asset_id"):
        validate_content_bundle(content_episode)


def test_legacy_script_shape_rejected() -> None:
    with pytest.raises(Exception):
        validate_script({
            "episode_id": "EP-CONTENT",
            "segments": [{"segment_id": "seg001", "text": "x", "purpose": "hook"}],
            "generated_at": _now(),
        })


def test_missing_asset_report_entry_rejected(content_episode: Path) -> None:
    path = content_episode / "work" / "content" / "storyboard.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["shots"][0]["missing_assets"] = ["需要标题素材"]
    data["shots"][0]["asset_ids"] = []
    data["shots"][0]["visual_type"] = "placeholder"
    data["asset_gaps"] = ["scene001"]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ContentValidationError, match="missing-assets.md"):
        validate_content_bundle(content_episode)


def test_cli_approve_then_assets_ready(
    content_episode: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = content_episode.parents[2]
    real_root = Path(__file__).resolve().parents[1]
    import shutil
    shutil.copytree(real_root / "config", root / "config")
    (root / "AGENTS.md").write_text("# test", encoding="utf-8")
    model = EpisodeModel.create("EP-CONTENT", mode="ORIGINAL")
    model.transition("INGESTED")
    model.complete_stage("ingest")
    model.save(content_episode / "episode.json")
    monkeypatch.setattr("avs.cli._find_project_root", lambda: root)

    runner = CliRunner()
    approve = runner.invoke(main, ["content", "approve", "EP-CONTENT"])
    assert approve.exit_code == 0, approve.output
    assert EpisodeModel.load(content_episode / "episode.json").status == "CONTENT_READY"
    assets = runner.invoke(main, ["assets", "approve", "EP-CONTENT"])
    assert assets.exit_code == 0, assets.output
    assert EpisodeModel.load(content_episode / "episode.json").status == "ASSETS_READY"
