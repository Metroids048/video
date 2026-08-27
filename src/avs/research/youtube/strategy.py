"""Rule extraction and research classification; never invent missing conditions."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .clean import _write_json


REQUIRED_FIELDS = ("entry", "exit", "stop_loss", "timeframe", "market_regime", "position_sizing")


def _rule_from_unit(unit: dict[str, Any]) -> dict[str, Any] | None:
    text = str(unit.get("content", ""))
    if not any(term in text for term in ("突破", "回踩", "入场", "做多", "做空", "止损", "止盈", "出场")):
        return None
    entry = text if any(term in text for term in ("入场", "做多", "做空", "突破", "回踩")) else None
    exit_value = text if any(term in text for term in ("出场", "止盈")) else None
    stop = text if "止损" in text else None
    timeframe = unit.get("timeframe") or None
    regime = unit.get("market") or None
    sizing = text if any(term in text for term in ("仓位", "风险", "每次")) else None
    values = {"entry": entry, "exit": exit_value, "stop_loss": stop, "timeframe": timeframe,
              "market_regime": regime, "position_sizing": sizing}
    missing = [field for field in REQUIRED_FIELDS if not values[field]]
    completeness = round((len(REQUIRED_FIELDS) - len(missing)) / len(REQUIRED_FIELDS), 4)
    return {"rule_id": f"RULE-{unit['unit_id']}", "name": text[:80], "source_units": [unit["unit_id"]],
            "source_videos": [unit["video_id"]], "source_timestamps": [{"video_id": unit["video_id"], "start_sec": unit["start_sec"], "end_sec": unit["end_sec"], "source_text": text}],
            "category": "ENTRY" if entry else "RISK", "market_scope": unit.get("market", []),
            "instrument_scope": unit.get("instrument", []), "timeframe_scope": unit.get("timeframe", []),
            "market_regime": unit.get("market", []), "preconditions": unit.get("conditions", []),
            "trigger": [text] if any(x in text for x in ("突破", "回踩")) else [], "confirmation": [],
            **values, "invalidation": unit.get("exceptions", []), "explicit_parameters": unit.get("parameters", []),
            "missing_fields": missing, "support_count": 1, "contradictions": [], "provenance": "SPEAKER_EXPLICIT",
            "completeness": completeness, "classification": "INCOMPLETE_RULE" if missing else "EXECUTABLE_CANDIDATE"}


def compile_rules(root: Path) -> dict[str, Any]:
    units_path = root / "agent_corpus" / "knowledge_units.jsonl"
    units = [json.loads(line) for line in units_path.read_text(encoding="utf-8").splitlines() if line.strip()] if units_path.exists() else []
    rules = [rule for unit in units if (rule := _rule_from_unit(unit))]
    research = root / "strategy_research"
    specs_dir = research / "strategy_specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (research / "rule_candidates.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rules), encoding="utf-8")
    incomplete = [x for x in rules if x["missing_fields"]]
    (research / "incomplete_rules.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in incomplete), encoding="utf-8")
    (research / "contradictions.jsonl").write_text("", encoding="utf-8")
    (research / "source_graph.jsonl").write_text("".join(json.dumps({"rule_id": x["rule_id"], "source_units": x["source_units"], "source_videos": x["source_videos"], "source_timestamps": x["source_timestamps"]}, ensure_ascii=False) + "\n" for x in rules), encoding="utf-8")
    complete = [x for x in rules if not x["missing_fields"]]
    specs: list[dict[str, Any]] = []
    for rule in complete:
        spec = {"strategy_id": f"STRAT-{rule['rule_id']}", "name": rule["name"], "source_rules": [rule["rule_id"]],
                "source_videos": rule["source_videos"], "market": rule["market_scope"], "timeframes": rule["timeframe_scope"],
                "regime_filter": {"value": rule["market_regime"], "provenance": "EXPLICIT_SOURCE"},
                "entry_long": {"condition": rule["entry"], "provenance": "EXPLICIT_SOURCE"}, "entry_short": {},
                "exit": {"condition": rule["exit"], "provenance": "EXPLICIT_SOURCE"},
                "stop_loss": {"condition": rule["stop_loss"], "provenance": "EXPLICIT_SOURCE"}, "take_profit": {},
                "position_sizing": {"condition": rule["position_sizing"], "provenance": "EXPLICIT_SOURCE"},
                "parameters": {"values": rule["explicit_parameters"], "provenance": "EXPLICIT_SOURCE"},
                "invalidation": rule["invalidation"], "source_provenance": "SPEAKER_EXPLICIT", "assumptions": [], "optimized_fields": []}
        specs.append(spec)
        _write_json(specs_dir / f"{spec['strategy_id']}.json", spec)
    status = "PASS" if complete else ("NO_PROMOTABLE_STRATEGY" if rules else "WAITING_FOR_INPUT")
    report = {"gate": "RULE_COMPILATION", "status": status, "rule_count": len(rules), "incomplete_count": len(incomplete), "strategy_spec_count": len(specs)}
    _write_json(research / "rule-compilation.json", report)
    return report


def run_quant_research(root: Path) -> dict[str, Any]:
    specs_dir = root / "strategy_research" / "strategy_specs"
    specs = list(specs_dir.glob("*.json")) if specs_dir.exists() else []
    status = "NO_PROMOTABLE_STRATEGY" if not specs else "RESEARCH_ONLY"
    report = {"gate": "QUANT_RESEARCH", "status": status, "strategies_tested": len(specs),
              "results": [], "promotion_authorized": False,
              "reason": "无现有研究/回测链或无完整规则；不得伪造盈利结果。" if not specs else "需要接入现有 canonical dataset、成本模型与 OOS 流程。"}
    _write_json(root / "strategy_research" / "reports" / "quant-research.json", report)
    return report
