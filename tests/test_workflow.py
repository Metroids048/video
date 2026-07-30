"""Tests for the V1.1 orchestration layer.

The orchestration layer may execute canonical CLI commands, but it must never own a
second state machine or auto-approve editorial work.
"""
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from avs.content import init_content_workspace
from avs.cli import main
from avs.models.episode import EpisodeModel
from avs.workflow import action_for_episode, run_automatic_steps


def _episode(tmp_path: Path, status: str = "CREATED") -> tuple[Path, EpisodeModel]:
    ep_dir = tmp_path / "episodes" / "active" / "WF-TEST"
    ep_dir.mkdir(parents=True)
    model = EpisodeModel.create("WF-TEST")
    for target in {
        "CREATED": (),
        "INGESTED": ("INGESTED",),
        "REFERENCE_READY": ("INGESTED", "REFERENCE_READY"),
        "CONTENT_READY": ("INGESTED", "CONTENT_READY"),
        "ASSETS_READY": ("INGESTED", "CONTENT_READY", "ASSETS_READY"),
        "DELIVERY_READY": (
            "INGESTED", "CONTENT_READY", "ASSETS_READY", "TIMELINE_READY",
            "ROUGH_CUT_READY", "QA_PASSED", "DELIVERY_READY",
        ),
    }[status]:
        model.transition(target)
    model.save(ep_dir / "episode.json")
    return ep_dir, model


def test_created_episode_starts_with_deterministic_ingest(tmp_path: Path) -> None:
    ep_dir, model = _episode(tmp_path)

    action = action_for_episode(ep_dir, model)

    assert action.kind == "command"
    assert action.command == ("ingest",)
    assert action.stage == "ingest"


def test_ingested_reference_video_runs_reference_analysis(tmp_path: Path) -> None:
    ep_dir, model = _episode(tmp_path, "INGESTED")
    reference = ep_dir / "input" / "reference" / "example.mp4"
    reference.parent.mkdir(parents=True)
    reference.write_bytes(b"reference")

    action = action_for_episode(ep_dir, model)

    assert action.kind == "command"
    assert action.command == ("reference", "analyze")
    assert action.stage == "reference"


def test_ingested_episode_initializes_content_then_stops_for_agent(tmp_path: Path) -> None:
    ep_dir, model = _episode(tmp_path, "INGESTED")

    before = action_for_episode(ep_dir, model)
    assert before.kind == "command"
    assert before.command == ("content", "init")

    init_content_workspace(ep_dir)
    after = action_for_episode(ep_dir, model)
    assert after.kind == "agent"
    assert after.stage == "content"
    assert "work/content/script.json" in after.required_artifacts


def test_content_ready_requires_explicit_asset_review(tmp_path: Path) -> None:
    ep_dir, model = _episode(tmp_path, "CONTENT_READY")

    action = action_for_episode(ep_dir, model)

    assert action.kind == "human"
    assert action.command == ("assets", "approve")
    assert action.stage == "assets"


def test_assets_ready_delegates_back_half_to_existing_run_command(tmp_path: Path) -> None:
    ep_dir, model = _episode(tmp_path, "ASSETS_READY")

    action = action_for_episode(ep_dir, model)

    assert action.kind == "command"
    assert action.command == ("run",)
    assert action.stage == "render_and_delivery"


def test_delivery_ready_is_a_terminal_completion(tmp_path: Path) -> None:
    ep_dir, model = _episode(tmp_path, "DELIVERY_READY")

    action = action_for_episode(ep_dir, model)

    assert action.kind == "complete"
    assert action.command is None


def test_resume_executes_only_safe_steps_until_agent_gate(tmp_path: Path) -> None:
    ep_dir, _ = _episode(tmp_path)
    commands: list[tuple[str, ...]] = []

    def fake_runner(command: tuple[str, ...], force: bool) -> None:
        commands.append(command)
        current = EpisodeModel.load(ep_dir / "episode.json")
        if command == ("ingest",):
            current.transition("INGESTED")
            current.save(ep_dir / "episode.json")
        elif command == ("content", "init"):
            init_content_workspace(ep_dir)
        else:  # pragma: no cover - protects the test's fake execution contract
            raise AssertionError(f"unexpected command: {command}")

    result = run_automatic_steps(ep_dir, command_runner=fake_runner)

    assert commands == [("ingest",), ("content", "init")]
    assert result.action.kind == "agent"
    assert result.executed_commands == commands


def test_workflow_next_is_registered_on_canonical_cli(tmp_path: Path, monkeypatch) -> None:
    ep_dir, model = _episode(tmp_path)
    monkeypatch.setattr("avs.cli_workflow._load_episode", lambda _episode_id: (ep_dir, model))

    result = CliRunner().invoke(main, ["workflow", "next", "WF-TEST", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "CREATED"
    assert payload["next_action"]["command"] == ["ingest"]
