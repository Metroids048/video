"""Agent-authored script contract tests.

The risk being tested is not "does the schema pass" but "can this script be
trusted on the publishable path": no invented evidence, no placeholders, no
deterministic fact-join wearing an ``authored_by: agent`` label.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from avs.creative.agent_script import (
    AgentScriptError,
    assert_agent_script,
    is_agent_authored,
    load_agent_script,
    script_summary,
    validate_agent_script,
)

MANIFEST = {
    "assets": [
        {"asset_id": "shot-a", "source_type": "screenshot", "must_use": True},
        {"asset_id": "rec-b", "source_type": "recording", "must_use": True},
        {"asset_id": "doc-c", "source_type": "document", "must_use": True},
    ]
}
INTELLIGENCE = {
    "assets": [
        {"asset_id": "shot-a", "regions": [{"region_id": "reject-panel"}]},
        {"asset_id": "rec-b", "regions": [{"region_id": "risk-veto"}]},
        {"asset_id": "doc-c", "regions": []},
    ]
}


def _segment(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "segment_id": "seg-002",
        "text": "系统收到信号后先拒单，这个拒绝原因被完整记录下来。",
        "spoken_text": "系统收到信号后先拒单，这个拒绝原因被完整记录下来。",
        "purpose": "展示风控拒单",
        "duration_seconds": 4.0,
        "evidence_required": True,
        "asset_refs": [{"asset_id": "shot-a", "region_id": "reject-panel"}],
        "reference_pattern_ids": ["PAT-004"],
    }
    payload.update(overrides)
    return payload


def _script(*, segments: list[dict[str, object]] | None = None, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "episode_id": "EP-AGENT",
        "authored_by": "agent",
        "author_id": "claude-opus-5",
        "hook_variant": "custom",
        "reference_pattern_ids": ["PAT-004"],
        "segments": segments if segments is not None else [
            {
                "segment_id": "seg-001",
                "text": "这个 AI 收到交易信号，第一件事是拒绝下单。",
                "spoken_text": "这个 AI 收到交易信号，第一件事是拒绝下单。",
                "purpose": "hook",
                "duration_seconds": 3.0,
                "evidence_required": False,
                "asset_refs": [],
                "reference_pattern_ids": ["PAT-004"],
                "narrative_beat": "制造反差",
                "visual_goal": "拒单弹窗特写",
            },
            _segment(),
        ],
    }
    payload.update(overrides)
    return payload


def _validate(script: dict[str, object]) -> list[str]:
    return validate_agent_script(
        script, manifest=MANIFEST, intelligence=INTELLIGENCE, episode_id="EP-AGENT",
    )


# ── happy path ────────────────────────────────────────────────────────


def test_well_formed_agent_script_passes() -> None:
    assert _validate(_script()) == []


def test_assert_returns_script_when_valid() -> None:
    script = _script()
    assert assert_agent_script(
        script, manifest=MANIFEST, intelligence=INTELLIGENCE, episode_id="EP-AGENT",
    ) is script


# ── authorship detection ──────────────────────────────────────────────


def test_missing_authored_by_treated_as_deterministic() -> None:
    assert is_agent_authored({"segments": []}) is False
    assert is_agent_authored({"authored_by": "deterministic"}) is False
    assert is_agent_authored({"authored_by": "agent"}) is True


def test_load_ignores_deterministic_script(tmp_path: Path) -> None:
    content = tmp_path / "work" / "content"
    content.mkdir(parents=True)
    (content / "script.json").write_text(
        json.dumps({"episode_id": "EP-X", "authored_by": "deterministic", "segments": []}),
        encoding="utf-8",
    )
    assert load_agent_script(tmp_path) is None


def test_load_returns_agent_script(tmp_path: Path) -> None:
    content = tmp_path / "work" / "content"
    content.mkdir(parents=True)
    (content / "script.json").write_text(json.dumps(_script()), encoding="utf-8")
    loaded = load_agent_script(tmp_path)
    assert loaded is not None and loaded["author_id"] == "claude-opus-5"


def test_load_survives_corrupt_json(tmp_path: Path) -> None:
    content = tmp_path / "work" / "content"
    content.mkdir(parents=True)
    (content / "script.json").write_text("{not json", encoding="utf-8")
    assert load_agent_script(tmp_path) is None


def test_load_missing_file(tmp_path: Path) -> None:
    assert load_agent_script(tmp_path) is None


# ── evidence integrity ────────────────────────────────────────────────


def test_evidence_segment_without_refs_rejected() -> None:
    errors = _validate(_script(segments=[
        _script()["segments"][0],
        _segment(evidence_required=True, asset_refs=[]),
    ]))
    assert any("没有 asset_refs" in item for item in errors)


def test_invented_asset_rejected() -> None:
    errors = _validate(_script(segments=[
        _script()["segments"][0],
        _segment(asset_refs=[{"asset_id": "does-not-exist", "region_id": "x"}]),
    ]))
    assert any("不是清单中的视觉素材" in item for item in errors)


def test_document_cannot_be_visual_evidence() -> None:
    # Documents inform the facts but must never be rendered as product footage.
    errors = _validate(_script(segments=[
        _script()["segments"][0],
        _segment(asset_refs=[{"asset_id": "doc-c", "region_id": "full-frame"}]),
    ]))
    assert any("不是清单中的视觉素材" in item for item in errors)


def test_invented_region_rejected() -> None:
    errors = _validate(_script(segments=[
        _script()["segments"][0],
        _segment(asset_refs=[{"asset_id": "shot-a", "region_id": "imaginary-panel"}]),
    ]))
    assert any("不存在区域" in item for item in errors)


def test_full_frame_region_always_allowed() -> None:
    assert _validate(_script(segments=[
        _script()["segments"][0],
        _segment(asset_refs=[{"asset_id": "shot-a", "region_id": "full-frame"}]),
    ])) == []


def test_non_evidence_segment_with_refs_rejected() -> None:
    errors = _validate(_script(segments=[
        _script()["segments"][0],
        _segment(evidence_required=False),
    ]))
    assert any("却绑定了 asset_refs" in item for item in errors)


# ── placeholder and laziness detection ────────────────────────────────


@pytest.mark.parametrize("bad", ["TODO 补充这里", "待补充产品说明", "placeholder text", "xxxx"])
def test_placeholder_text_rejected(bad: str) -> None:
    errors = _validate(_script(segments=[
        _script()["segments"][0],
        _segment(spoken_text=bad, text=bad, duration_seconds=2.0),
    ]))
    assert any("占位符文本" in item for item in errors)


def test_fact_join_masquerading_as_agent_work_rejected() -> None:
    """The exact failure mode this round exists to prevent."""
    joined = "显示拒单原因；显示回测记录；不声称实盘盈利"
    errors = _validate(_script(segments=[
        _script()["segments"][0],
        _segment(segment_id="seg-002", spoken_text=joined, text=joined, duration_seconds=5.0),
        _segment(segment_id="seg-003", spoken_text=joined, text=joined, duration_seconds=5.0),
    ]))
    assert any("与确定性规划器输出无区别" in item for item in errors)


def test_single_semicolon_segment_not_flagged() -> None:
    # One list-like line is legitimate writing; the pattern only matters at scale.
    errors = _validate(_script(segments=[
        _script()["segments"][0],
        _segment(segment_id="seg-002", spoken_text="信号不足；风险超限，两种情况都会被拒单。",
                 text="x", duration_seconds=4.0),
        _segment(segment_id="seg-003",
                 spoken_text="真正花时间的是把每次拒绝的原因留下来。", text="y",
                 duration_seconds=4.0),
    ]))
    assert not any("与确定性规划器输出无区别" in item for item in errors)


# ── pacing sanity ─────────────────────────────────────────────────────


def test_unreadably_dense_narration_rejected() -> None:
    errors = _validate(_script(segments=[
        _script()["segments"][0],
        _segment(spoken_text="这段话非常长以至于根本不可能在很短的时间里读完它" * 2,
                 text="x", duration_seconds=1.0),
    ]))
    assert any("字/秒 超过" in item for item in errors)


def test_too_sparse_narration_rejected() -> None:
    errors = _validate(_script(segments=[
        _script()["segments"][0],
        _segment(spoken_text="好", text="好", duration_seconds=8.0),
    ]))
    assert any("字/秒 低于" in item for item in errors)


def test_out_of_range_duration_rejected() -> None:
    errors = _validate(_script(segments=[
        _script()["segments"][0],
        _segment(duration_seconds=30.0),
    ]))
    assert any("超出" in item for item in errors)


# ── structure ─────────────────────────────────────────────────────────


def test_hook_must_be_first_and_evidence_free() -> None:
    errors = _validate(_script(segments=[_segment(segment_id="seg-001")]))
    assert any("首段必须是 Hook" in item for item in errors)


def test_duplicate_segment_ids_rejected() -> None:
    errors = _validate(_script(segments=[
        _script()["segments"][0],
        _segment(segment_id="seg-002"),
        _segment(segment_id="seg-002"),
    ]))
    assert any("segment_id 重复" in item for item in errors)


def test_episode_id_mismatch_rejected() -> None:
    errors = _validate(_script(episode_id="EP-WRONG"))
    assert any("episode_id 不匹配" in item for item in errors)


def test_schema_violation_short_circuits() -> None:
    errors = _validate(_script(hook_variant="not-a-variant"))
    assert len(errors) == 1 and errors[0].startswith("Schema 校验失败")


def test_assert_raises_on_invalid() -> None:
    with pytest.raises(AgentScriptError):
        assert_agent_script(
            _script(episode_id="EP-WRONG"),
            manifest=MANIFEST, intelligence=INTELLIGENCE, episode_id="EP-AGENT",
        )


def test_summary_reports_creative_fields() -> None:
    summary = script_summary(_script())
    assert summary["authored_by"] == "agent"
    assert summary["has_narrative_beats"] is True
    assert summary["has_visual_goals"] is True
    assert summary["segment_count"] == 2
    assert summary["evidence_segments"] == 1
    assert summary["total_duration"] == pytest.approx(7.0)


def test_deterministic_script_still_validates_against_schema() -> None:
    """Backward compatibility: existing plan_script output must stay legal."""
    from avs.creative import build_creative_brief, plan_script, select_reference_patterns

    brief = build_creative_brief("EP-COMPAT", must_use_asset_ids=["a"])
    selection = select_reference_patterns("EP-COMPAT", pattern_ids=["PAT-004"])
    script = plan_script(
        brief,
        {"assets": [{"asset_id": "a", "visible_facts": ["显示拒单原因"],
                     "regions": [{"region_id": "reject"}],
                     "metadata": {"source_type": "screenshot"}}]},
        selection,
    )
    assert is_agent_authored(script) is False
