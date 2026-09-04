"""Continuous Clean Corpus -> Agent Corpus -> Rule -> Research loop."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .agent_corpus import agent_corpus_gate, build_agent_corpus, build_video_knowledge
from .clean import ASR_ALIASES, clean_corpus_gate, clean_video, _read_json
from .storage import load_catalog
from .strategy import compile_rules, run_quant_research


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def migrate_legacy_reports(root: Path) -> None:
    """Make legacy corpus-final non-authoritative without deleting user evidence."""
    report = root / "reports" / "corpus-final.json"
    if report.exists():
        archive = root / "reports" / "archive" / "corpus-final-legacy.json"
        archive.parent.mkdir(parents=True, exist_ok=True)
        if not archive.exists():
            shutil.copy2(report, archive)
        _write(report, {"deprecated": True, "reason": "superseded by current-state.json", "superseded_by": "reports/current-state.json"})


def write_agent_readme(root: Path, *, agent_ready: bool) -> None:
    channel = "YouTube Corpus"
    if (root / "channel.json").exists():
        try:
            channel = (json.loads((root / "channel.json").read_text(encoding="utf-8")) or {}).get("title") or channel
        except json.JSONDecodeError:
            pass
    if agent_ready:
        text = (f"# {channel}\n\n读取层级：\n\nL1 Agent Corpus：`agent_corpus/README.md`、`agent_corpus/CHANNEL_MAP.md`、`agent_corpus/TOPIC_INDEX.md`\n"
                "L2 Clean Transcript：`videos/<id>/clean/transcript.cleaned.md`\nL3 Raw Transcript：`videos/<id>/transcript/transcript.md`\n"
                "L4 Raw canonical/timestamps：`videos/<id>/transcript/canonical.json`\n\n规则研究入口：`strategy_research/`。原始证据永不覆盖。\n")
    else:
        text = (f"# {channel}\n\nClean Corpus 尚未完成。先查看 `clean_corpus/semantic-review.jsonl`，再按 `videos/<id>/clean/transcript.cleaned.md` → `videos/<id>/transcript/transcript.md` → `videos/<id>/transcript/canonical.json` 逐段复核。\n"
                "清洗完成后自动切换到 `agent_corpus/`；原始证据永不覆盖。\n")
    (root / "README_FOR_AGENTS.md").write_text(text, encoding="utf-8")


def write_clean_corpus_outputs(root: Path, rows: list[dict[str, Any]], clean_gate: dict[str, Any]) -> None:
    corpus = root / "clean_corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    aliases = {alias: {"canonical_term": data["canonical_term"], "aliases": [alias],
                       "context_terms": list(data["context_terms"]), "confidence": data["confidence"],
                       "correction_mode": "LEXICON_CONTEXT"} for alias, data in ASR_ALIASES.items()}
    _write(corpus / "asr_aliases.json", aliases)
    glossary = sorted({term for data in aliases.values() for term in [data["canonical_term"], *data["context_terms"]]})
    _write(corpus / "glossary.json", {"version": "v1", "terms": glossary})
    clean_index: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    semantic_review: list[dict[str, Any]] = []
    correction_count = 0
    for row in rows:
        vid = str(row["video_id"])
        qa = _read_json(root / "videos" / vid / "clean" / "clean_qa.json", {}) or {}
        clean_index.append({"video_id": vid, "status": qa.get("status", "NOT_PROCESSED"),
                            "cleaned": f"videos/{vid}/clean/cleaned.json",
                            "transcript_cleaned": f"videos/{vid}/clean/transcript.cleaned.md",
                            "correction_map": f"videos/{vid}/clean/correction_map.jsonl"})
        correction_path = root / "videos" / vid / "clean" / "correction_map.jsonl"
        if correction_path.exists():
            correction_count += sum(1 for line in correction_path.read_text(encoding="utf-8").splitlines() if line.strip())
        unresolved_path = root / "videos" / vid / "clean" / "unresolved.jsonl"
        if unresolved_path.exists():
            unresolved.extend(json.loads(line) | {"video_id": vid} for line in unresolved_path.read_text(encoding="utf-8").splitlines() if line.strip())
        semantic_path = root / "videos" / vid / "clean" / "semantic_review.jsonl"
        if semantic_path.exists():
            semantic_review.extend(json.loads(line) for line in semantic_path.read_text(encoding="utf-8").splitlines() if line.strip())
    (corpus / "clean-index.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in clean_index), encoding="utf-8")
    (corpus / "unresolved-critical.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in unresolved if x.get("critical")), encoding="utf-8")
    (corpus / "semantic-review.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in semantic_review), encoding="utf-8")
    _write(corpus / "corrections-summary.json", {"videos": len(rows), "correction_count": correction_count, "unresolved_count": len(unresolved), "critical_unresolved_count": sum(bool(x.get("critical")) for x in unresolved), "semantic_review_count": len(semantic_review)})
    _write(root / "reports" / "clean-corpus-final.json", {**clean_gate, "artifacts": {"index": "clean_corpus/clean-index.jsonl", "critical": "clean_corpus/unresolved-critical.jsonl", "semantic_review": "clean_corpus/semantic-review.jsonl"}})


def run_research_pipeline(root: Path, *, resume: bool = True) -> dict[str, Any]:
    rows = load_catalog(root)
    migrate_legacy_reports(root)
    # Every accessible transcript is processed; terminal unavailable rows stay explicit and are never counted as clean.
    clean_results = [clean_video(root, row, resume=resume) for row in rows if str(row.get("extraction_status")) in {"TRANSCRIPT_QA_PASSED", "CONTENT_QA_PASSED", "CLEAN_QA_PASSED"}]
    clean_gate = clean_corpus_gate(root, rows)
    write_clean_corpus_outputs(root, rows, clean_gate)
    if clean_gate["status"] == "PASS":
        knowledge_results = [build_video_knowledge(root, row, resume=resume) for row in rows if str(row.get("extraction_status")) in {"TRANSCRIPT_QA_PASSED", "CONTENT_QA_PASSED", "CLEAN_QA_PASSED"}]
        agent_summary = build_agent_corpus(root, rows)
        agent_gate = agent_corpus_gate(root, rows)
    else:
        knowledge_results, agent_summary, agent_gate = [], {}, {"gate": "AGENT_CORPUS", "status": "WAITING_FOR_INPUT", "accessible": clean_gate.get("accessible", 0), "included": 0}
    if agent_gate["status"] == "PASS":
        rule_gate = compile_rules(root)
    else:
        rule_gate = {"gate": "RULE_COMPILATION", "status": "WAITING_FOR_INPUT", "rule_count": 0, "incomplete_count": 0, "strategy_spec_count": 0}
    if rule_gate["status"] in {"PASS", "NO_PROMOTABLE_STRATEGY"}:
        research_gate = run_quant_research(root)
    else:
        research_gate = {"gate": "QUANT_RESEARCH", "status": "WAITING_FOR_INPUT", "strategies_tested": 0, "promotion_authorized": False}
    write_agent_readme(root, agent_ready=agent_gate["status"] == "PASS")
    state = {"pipeline": "QINXIONGMAO_RESEARCH_PIPELINE", "clean_corpus": clean_gate, "agent_corpus": agent_gate,
             "rule_compilation": rule_gate, "quant_research": research_gate, "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}
    _write(root / "reports" / "current-state.json", state)
    # Normal completion is explicit; no strategy is not a technical failure.
    # RESEARCH_ONLY means specs exist but real backtest/OOS evidence is still
    # missing; only an explicit no-promotable conclusion closes the loop.
    state["status"] = "COMPLETE" if research_gate["status"] == "NO_PROMOTABLE_STRATEGY" else "IN_PROGRESS"
    _write(root / "reports" / "current-state.json", state)
    return {"state": state, "clean_results": clean_results, "knowledge_results": knowledge_results, "agent_summary": agent_summary}
