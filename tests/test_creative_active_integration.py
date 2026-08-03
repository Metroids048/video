"""Integration tests proving creative inputs alter downstream plans."""
from __future__ import annotations

from avs.creative import (
    build_creative_brief,
    build_evidence_map,
    plan_script,
    plan_shots,
    select_reference_patterns,
)


INTELLIGENCE = {
    "assets": [
        {"asset_id": "a", "visible_facts": ["显示拒单原因"], "regions": [{"region_id": "reject"}]},
        {"asset_id": "b", "visible_facts": ["显示回测记录"], "regions": [{"region_id": "backtest"}]},
    ]
}


def _pipeline(*, hook: str, assets: list[str], patterns: list[str]):
    brief = build_creative_brief("EP-PLAN", must_use_asset_ids=assets, hook_variant=hook)
    selection = select_reference_patterns("EP-PLAN", pattern_ids=patterns)
    script = plan_script(brief, INTELLIGENCE, selection, hook_variant=hook)
    evidence = build_evidence_map("EP-PLAN", script, intelligence=INTELLIGENCE)
    shots = plan_shots("EP-PLAN", evidence, selection=selection)
    return script, evidence, shots


def test_hook_changes_first_script_and_shot() -> None:
    result = _pipeline(hook="result", assets=["a"], patterns=["PAT-004"])
    conflict = _pipeline(hook="conflict", assets=["a"], patterns=["PAT-004"])
    assert result[0]["segments"][0]["spoken_text"] != conflict[0]["segments"][0]["spoken_text"]
    assert result[2]["shots"][0]["spoken_text"] != conflict[2]["shots"][0]["spoken_text"]


def test_must_use_changes_evidence_map() -> None:
    one = _pipeline(hook="result", assets=["a"], patterns=["PAT-004"])
    two = _pipeline(hook="result", assets=["a", "b"], patterns=["PAT-004"])
    one_refs = {ref["asset_id"] for item in one[1]["segments"] for ref in item["asset_refs"]}
    two_refs = {ref["asset_id"] for item in two[1]["segments"] for ref in item["asset_refs"]}
    assert one_refs == {"a"}
    assert two_refs == {"a", "b"}


def test_reference_pattern_changes_shot_plan() -> None:
    hook = _pipeline(hook="result", assets=["a"], patterns=["PAT-004"])[2]
    pacing = _pipeline(hook="result", assets=["a"], patterns=["PAT-009"])[2]
    assert hook["shots"][0]["reference_pattern_ids"] != pacing["shots"][0]["reference_pattern_ids"]


def test_nonvisual_inputs_do_not_become_product_shots() -> None:
    intelligence = {
        "assets": [
            {"asset_id": "screen", "visible_facts": ["显示账户结构"], "regions": [{"region_id": "account"}], "metadata": {"source_type": "screenshot"}},
            {"asset_id": "notes", "visible_facts": ["说明系统边界"], "regions": [{"region_id": "text"}], "metadata": {"source_type": "document"}},
        ]
    }
    brief = build_creative_brief("EP-NONVISUAL", must_use_asset_ids=["screen", "notes"], hook_variant="result")
    selection = select_reference_patterns("EP-NONVISUAL", pattern_ids=["PAT-004"])
    script = plan_script(brief, intelligence, selection, hook_variant="result")
    refs = {ref["asset_id"] for segment in script["segments"] for ref in segment["asset_refs"]}
    assert refs == {"screen"}


def test_multiple_facts_from_one_asset_become_one_narrative_segment() -> None:
    intelligence = {
        "assets": [{
            "asset_id": "screen",
            "visible_facts": ["展示策略参数", "展示拒单阈值", "不声称实盘盈利"],
            "regions": [{"region_id": "risk", "priority": 0.9}],
            "metadata": {"source_type": "screenshot"},
        }],
    }
    brief = build_creative_brief("EP-GROUPED", must_use_asset_ids=["screen"])
    selection = select_reference_patterns("EP-GROUPED", pattern_ids=["PAT-004"])

    script = plan_script(brief, intelligence, selection)

    assert len(script["segments"]) == 2
    segment = script["segments"][1]
    assert segment["asset_refs"] == [{"asset_id": "screen", "region_id": "risk"}]
    assert "策略参数" in segment["spoken_text"]
    assert "拒单阈值" in segment["spoken_text"]
