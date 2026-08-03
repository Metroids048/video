"""Evidence-first script planning."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from avs.creative.brief import HOOKS

_SCHEMA = Path(__file__).resolve().parents[3] / "schemas" / "active-script.schema.json"


def _facts(intelligence: dict[str, Any], must_use: list[str]) -> list[tuple[str, str, list[str]]]:
    by_id = {item.get("asset_id"): item for item in intelligence.get("assets", [])}
    facts: list[tuple[str, str, list[str]]] = []
    for asset_id in must_use:
        item = by_id.get(asset_id)
        if not item:
            continue
        source_type = (item.get("metadata") or {}).get("source_type")
        if source_type in {"document", "text", "link", "audio"}:
            # 文档、文字和音频参与事实分析/音频链路，但不能被误渲染成
            # 产品画面。只有真实视觉素材才能生成证据镜头。
            continue
        visible = item.get("visible_facts") or []
        if visible:
            regions = sorted(
                item.get("regions") or [],
                key=lambda region: float(region.get("priority", 0.0)),
                reverse=True,
            )
            region_id = regions[0].get("region_id", "full-frame") if regions else "full-frame"
            facts.append((asset_id, region_id, [str(fact) for fact in visible]))
    return facts


def plan_script(
    brief: dict[str, Any],
    intelligence: dict[str, Any],
    selection: dict[str, Any],
    *,
    hook_variant: str | None = None,
) -> dict[str, Any]:
    variant = hook_variant or next(
        (item["id"] for item in brief.get("hook_variants", []) if item.get("text") == brief.get("hook")),
        "conflict",
    )
    pattern_ids = [item["pattern_id"] for item in selection.get("selections", [])]
    if not pattern_ids:
        raise ValueError("脚本不能在没有具体 reference pattern ID 时生成")
    segments: list[dict[str, Any]] = [{
        "segment_id": "seg-001",
        "text": HOOKS.get(variant, brief["hook"]),
        "spoken_text": HOOKS.get(variant, brief["hook"]),
        "purpose": "hook",
        "duration_seconds": 3.0,
        "evidence_required": False,
        "asset_refs": [],
        "reference_pattern_ids": pattern_ids,
    }]
    facts = _facts(intelligence, list(brief.get("must_use_asset_ids", [])))
    for idx, (asset_id, region_id, asset_facts) in enumerate(facts, start=2):
        spoken_text = "；".join(asset_facts)
        duration = max(2.6, min(4.5, len(spoken_text.replace(" ", "")) / 5.5))
        segments.append({
            "segment_id": f"seg-{idx:03d}",
            "text": spoken_text,
            "spoken_text": spoken_text,
            "purpose": "展示真实产品事实",
            "duration_seconds": round(duration, 2),
            "evidence_required": True,
            "asset_refs": [{"asset_id": asset_id, "region_id": region_id}],
            "reference_pattern_ids": pattern_ids,
        })
    result = {
        "episode_id": brief["episode_id"],
        "segments": segments,
        "hook_variant": variant,
        "reference_pattern_ids": pattern_ids,
    }
    jsonschema.Draft7Validator(json.loads(_SCHEMA.read_text(encoding="utf-8"))).validate(result)
    return result
