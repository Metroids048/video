"""The publishable path must run through Agent-authored content, not stop at it.

Before this round the workflow paused for a human hook choice and, when it did
run automatically, `plan` regenerated over whatever the Agent had written.  These
tests pin both halves: a trustworthy Agent script turns the gate into a command,
and an untrustworthy one keeps the gate closed.
"""
from __future__ import annotations

import json
from pathlib import Path

from avs.models.episode import EpisodeModel
from avs.workflow import action_for_episode, run_automatic_steps

MANIFEST = {
    "assets": [
        {"asset_id": "shot-a", "source_type": "screenshot", "must_use": True, "status": "ok"},
    ]
}
INTELLIGENCE = {
    "assets": [{"asset_id": "shot-a", "regions": [{"region_id": "panel"}]}],
}


def _agent_script(episode_id: str = "WF-AGENT") -> dict[str, object]:
    return {
        "episode_id": episode_id,
        "authored_by": "agent",
        "author_id": "claude-opus-5",
        "hook_variant": "custom",
        "angle": "先给结论再解释机制",
        "reference_pattern_ids": ["PAT-004"],
        "segments": [
            {
                "segment_id": "seg-001",
                "text": "这个 AI 收到信号后第一件事是拒绝下单。",
                "spoken_text": "这个 AI 收到信号后第一件事是拒绝下单。",
                "purpose": "hook",
                "duration_seconds": 3.0,
                "evidence_required": False,
                "asset_refs": [],
                "reference_pattern_ids": ["PAT-004"],
                "narrative_beat": "制造反差",
                "visual_goal": "拒单弹窗特写",
            },
            {
                "segment_id": "seg-002",
                "text": "拒绝的原因被完整记录，这才是可审计的关键。",
                "spoken_text": "拒绝的原因被完整记录，这才是可审计的关键。",
                "purpose": "解释机制",
                "duration_seconds": 4.0,
                "evidence_required": True,
                "asset_refs": [{"asset_id": "shot-a", "region_id": "panel"}],
                "reference_pattern_ids": ["PAT-004"],
                "narrative_beat": "揭示机制",
                "visual_goal": "拒单原因列表局部放大",
            },
        ],
    }


def _publishable_episode(tmp_path: Path, *, script: dict[str, object] | None = None) -> tuple[Path, EpisodeModel]:
    ep_dir = tmp_path / "episodes" / "active" / "WF-AGENT"
    (ep_dir / "work" / "content").mkdir(parents=True)
    (ep_dir / "work" / "analysis").mkdir(parents=True)
    (ep_dir / "work" / "input-manifest.json").write_text(
        json.dumps(MANIFEST), encoding="utf-8",
    )
    (ep_dir / "work" / "analysis" / "asset-intelligence.json").write_text(
        json.dumps(INTELLIGENCE), encoding="utf-8",
    )
    if script is not None:
        (ep_dir / "work" / "content" / "script.json").write_text(
            json.dumps(script, ensure_ascii=False), encoding="utf-8",
        )
    # ORIGINAL mode is publishable by construction; the flag is read-only.
    model = EpisodeModel.create("WF-AGENT")
    model.transition("INGESTED")
    assert model.publishable
    model.complete_stage("ingest")
    model.complete_stage("analyze")
    model.save(ep_dir / "episode.json")
    return ep_dir, model


def test_gate_is_agent_action_when_no_script(tmp_path: Path) -> None:
    ep_dir, model = _publishable_episode(tmp_path)

    action = action_for_episode(ep_dir, model)

    assert action.kind == "agent"
    assert action.stage == "content"
    assert "work/content/script.json" in action.required_artifacts
    # The Agent must be told the machine-checkable contract, not just "write a script".
    assert "authored_by=agent" in action.summary


def test_valid_agent_script_turns_gate_into_command(tmp_path: Path) -> None:
    ep_dir, model = _publishable_episode(tmp_path, script=_agent_script())

    action = action_for_episode(ep_dir, model)

    assert action.kind == "command", "有可信 Agent 脚本时必须能自动续跑"
    assert action.command == ("plan",)


def test_deterministic_script_does_not_open_the_gate(tmp_path: Path) -> None:
    script = _agent_script()
    script["authored_by"] = "deterministic"
    ep_dir, model = _publishable_episode(tmp_path, script=script)

    assert action_for_episode(ep_dir, model).kind == "agent"


def test_untrustworthy_agent_script_keeps_gate_closed(tmp_path: Path) -> None:
    script = _agent_script()
    # Evidence pointing at an asset that does not exist in the manifest.
    script["segments"][1]["asset_refs"] = [{"asset_id": "ghost", "region_id": "panel"}]
    ep_dir, model = _publishable_episode(tmp_path, script=script)

    action = action_for_episode(ep_dir, model)

    assert action.kind == "agent", "校验失败的脚本不得被当作可用脚本放行"


def test_fact_join_relabelled_as_agent_keeps_gate_closed(tmp_path: Path) -> None:
    script = _agent_script()
    joined = "显示拒单原因；显示回测记录；不声称实盘盈利"
    script["segments"][1]["spoken_text"] = joined
    script["segments"].append({
        "segment_id": "seg-003",
        "text": joined, "spoken_text": joined,
        "purpose": "展示事实", "duration_seconds": 5.0,
        "evidence_required": True,
        "asset_refs": [{"asset_id": "shot-a", "region_id": "panel"}],
        "reference_pattern_ids": ["PAT-004"],
    })
    ep_dir, model = _publishable_episode(tmp_path, script=script)

    assert action_for_episode(ep_dir, model).kind == "agent"


def test_corrupt_script_keeps_gate_closed(tmp_path: Path) -> None:
    ep_dir, model = _publishable_episode(tmp_path)
    (ep_dir / "work" / "content" / "script.json").write_text("{broken", encoding="utf-8")

    assert action_for_episode(ep_dir, model).kind == "agent"


def test_gate_check_creates_no_files(tmp_path: Path) -> None:
    ep_dir, model = _publishable_episode(tmp_path, script=_agent_script())
    before = {path for path in ep_dir.rglob("*") if path.is_file()}

    action_for_episode(ep_dir, model)

    assert {path for path in ep_dir.rglob("*") if path.is_file()} == before


def test_resume_stops_at_agent_gate_without_script(tmp_path: Path) -> None:
    ep_dir, _ = _publishable_episode(tmp_path)
    executed: list[tuple[str, ...]] = []

    result = run_automatic_steps(
        ep_dir,
        command_runner=lambda command, force: executed.append(command) or 0,
    )

    assert executed == []
    assert result.action.kind == "agent"


def test_resume_runs_plan_when_agent_script_present(tmp_path: Path) -> None:
    ep_dir, _ = _publishable_episode(tmp_path, script=_agent_script())
    executed: list[tuple[str, ...]] = []

    def runner(command: tuple[str, ...], force: bool) -> int:
        executed.append(command)
        model = EpisodeModel.load(ep_dir / "episode.json")
        model.complete_stage(command[0])
        model.save(ep_dir / "episode.json")
        return 0

    run_automatic_steps(ep_dir, command_runner=runner)

    assert ("plan",) in executed, "Agent 脚本就位后 resume 必须自动执行 plan"
