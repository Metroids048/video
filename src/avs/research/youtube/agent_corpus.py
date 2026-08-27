"""Build the Agent-ready knowledge layer from clean transcripts."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .clean import _read_json, _write_json
from .storage import load_catalog, load_channel


BOILERPLATE = ("点赞", "关注", "订阅", "课程", "加微信", "直播间", "免责声明", "感谢观看")
RULE_TERMS = ("如果", "当", "只有", "突破", "回踩", "入场", "做多", "做空", "止损", "止盈", "出场")


def _classify(text: str) -> str:
    if any(x in text for x in ("风险", "注意", "不要", "不能")):
        return "WARNING"
    if any(x in text for x in ("例如", "比如", "案例")):
        return "EXAMPLE"
    if any(x in text for x in ("定义", "是指", "意味着")):
        return "DEFINITION"
    if any(x in text for x in RULE_TERMS):
        return "RULE_STATEMENT"
    if any(x in text for x in ("周期", "级别", "小时", "分钟", "日线", "周线")):
        return "TIMEFRAME"
    return "OPINION" if any(x in text for x in ("我认为", "我觉得", "个人")) else "PRINCIPLE"


def build_video_knowledge(root: Path, row: dict[str, Any], *, resume: bool = True) -> dict[str, Any]:
    video_id = str(row["video_id"])
    vroot = root / "videos" / video_id
    clean = _read_json(vroot / "clean" / "cleaned.json", {}) or {}
    if not clean:
        return {"video_id": video_id, "status": "WAITING_FOR_INPUT", "reason": "CLEAN_TRANSCRIPT_MISSING"}
    knowledge_root = vroot / "knowledge"
    qa_path = knowledge_root / "knowledge_qa.json"
    if resume and qa_path.exists() and (_read_json(qa_path, {}) or {}).get("status") == "AGENT_KNOWLEDGE_READY":
        return {"video_id": video_id, "status": "SKIPPED", **(_read_json(qa_path, {}) or {})}
    units: list[dict[str, Any]] = []
    for index, segment in enumerate(clean.get("segments", []), 1):
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        label = "BOILERPLATE" if any(term in text for term in BOILERPLATE) else "CORE_CONTENT"
        units.append({"unit_id": f"KU-{video_id}-{index:04d}", "video_id": video_id,
                      "start_sec": segment.get("start", 0), "end_sec": segment.get("end", 0),
                      "type": _classify(text), "topic": _topics(text), "content": text,
                      "market": _markets(text), "instrument": _instruments(text),
                      "timeframe": _timeframes(text), "conditions": [text] if any(x in text for x in ("如果", "只有", "当", "前提")) else [],
                      "exceptions": [text] if any(x in text for x in ("除非", "但是", "否则")) else [],
                      "parameters": re.findall(r"(?:\d+(?:\.\d+)?%?|\d+(?:分钟|小时)|日线|周线)", text),
                      "risks": [text] if label == "CORE_CONTENT" and any(x in text for x in ("风险", "止损")) else [],
                      "speaker_claim": True, "source_provenance": "SPEAKER_EXPLICIT",
                      "clean_source_refs": [f"cleaned.json#segments/{index - 1}"],
                      "raw_source_refs": [f"transcript/canonical.json#segments/{index - 1}"],
                      "priority": label})
    knowledge_root.mkdir(parents=True, exist_ok=True)
    (knowledge_root / "units.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in units), encoding="utf-8")
    sections = {key: [u["content"] for u in units if u["type"] == kind or (key == "核心主题" and u["priority"] == "CORE_CONTENT")] for key, kind in {
        "概念和定义": "DEFINITION", "作者实际给出的判断方法": "PRINCIPLE", "条件和前提": "RULE_STATEMENT",
        "入场相关内容": "ENTRY_DISCUSSION", "出场相关内容": "EXIT_DISCUSSION", "止损和风险": "WARNING",
        "案例": "EXAMPLE", "作者主张": "OPINION", "不确定内容": "UNCERTAIN",
    }.items()}
    lines = [f"# {row.get('title') or video_id}", "", "## 核心主题", "", *[u["content"] for u in units if u["priority"] == "CORE_CONTENT"][:8], ""]
    for title, values in sections.items():
        lines.extend([f"## {title}", "", *(f"- {v}" for v in values), ""])
    lines.extend(["## Sources", "", "每条知识单元均保留 clean 与 raw transcript 引用。", ""])
    (knowledge_root / "content.md").write_text("\n".join(lines), encoding="utf-8")
    qa = {"status": "AGENT_KNOWLEDGE_READY", "unit_count": len(units), "core_content_count": sum(u["priority"] == "CORE_CONTENT" for u in units),
          "source_complete": all(u["clean_source_refs"] and u["raw_source_refs"] for u in units)}
    _write_json(qa_path, qa)
    return {"video_id": video_id, "status": qa["status"], **qa}


def _topics(text: str) -> list[str]:
    mapping = {"Support Resistance": ("支撑", "压力", "关键位"), "Trend": ("趋势", "顺势", "逆势"),
               "Breakout": ("突破", "假突破", "回踩"), "Fibonacci": ("斐波那契", "回撤"),
               "Harmonic": ("谐波", "AB=CD", "蝴蝶", "螃蟹"), "Risk Management": ("止损", "止盈", "仓位", "盈亏比"),
               "Price Action": ("价格行为", "裸K", "Pin Bar"), "MACD": ("MACD", "背离"),
               "Trading Psychology": ("心理", "情绪", "纪律"), "Multi-Timeframe": ("周期", "级别", "多周期")}
    return [name for name, terms in mapping.items() if any(term in text for term in terms)] or ["General"]


def _markets(text: str) -> list[str]:
    return [x for x in ("牛市", "熊市", "震荡", "趋势") if x in text]


def _instruments(text: str) -> list[str]:
    return [x for x in ("BTC", "ETH", "黄金", "外汇") if x.lower() in text.lower()]


def _timeframes(text: str) -> list[str]:
    return re.findall(r"(?:\d+\s*[mMhHdD]|\d+\s*分钟|\d+\s*小时|日线|周线|月线)", text)


def build_agent_corpus(root: Path, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = rows if rows is not None else load_catalog(root)
    corpus = root / "agent_corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    topics: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_units: list[dict[str, Any]] = []
    video_lines = ["# VIDEO_INDEX", ""]
    included = 0
    for row in rows:
        vid = str(row["video_id"])
        units_path = root / "videos" / vid / "knowledge" / "units.jsonl"
        units = [json.loads(line) for line in units_path.read_text(encoding="utf-8").splitlines() if line.strip()] if units_path.exists() else []
        if units:
            included += 1
        video_lines.append(f"- **{row.get('title') or vid}** (`{vid}`) — [knowledge](../videos/{vid}/knowledge/content.md) — [clean](../videos/{vid}/clean/transcript.cleaned.md)")
        for unit in units:
            all_units.append(unit)
            for topic in unit["topic"]:
                topics[topic].append(unit)
    (corpus / "VIDEO_INDEX.md").write_text("\n".join(video_lines) + "\n", encoding="utf-8")
    topic_lines = ["# TOPIC_INDEX", ""]
    (corpus / "topics").mkdir(exist_ok=True)
    for topic, units in sorted(topics.items()):
        slug = re.sub(r"[^a-z0-9-]+", "-", topic.lower()).strip("-") or "topic"
        topic_lines.append(f"- [{topic}](topics/{slug}.md) ({len(units)} units)")
        (corpus / "topics" / f"{slug}.md").write_text("\n".join([f"# {topic}", "", *[f"- `{u['video_id']}` @ {u['start_sec']}s: {u['content']}" for u in units]]) + "\n", encoding="utf-8")
    (corpus / "TOPIC_INDEX.md").write_text("\n".join(topic_lines) + "\n", encoding="utf-8")
    channel = load_channel(root) if (root / "channel.json").exists() else {}
    (corpus / "CHANNEL_MAP.md").write_text(f"# {channel.get('title') or channel.get('handle') or 'YouTube Corpus'}\n\n视频数：{len(rows)}\n知识单元：{len(all_units)}\n", encoding="utf-8")
    (corpus / "GLOSSARY.md").write_text("# GLOSSARY\n\n术语以 clean_corpus/glossary.json 为准。\n", encoding="utf-8")
    (corpus / "knowledge_units.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in all_units), encoding="utf-8")
    claims = [{"claim_id": u["unit_id"], "video_id": u["video_id"], "claim": u["content"],
               "source_refs": u["clean_source_refs"], "speaker_claim": u["speaker_claim"]} for u in all_units if u["speaker_claim"]]
    (corpus / "claims.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in claims), encoding="utf-8")
    # Contradictions are deliberately evidence-backed; no heuristic claim is
    # emitted as a contradiction without at least two source units.
    (corpus / "contradictions.jsonl").write_text("", encoding="utf-8")
    chunks = [{"chunk_id": f"CHUNK-{i // 8 + 1:04d}", "topics": u["topic"], "video_ids": [u["video_id"]],
               "start_sec": u["start_sec"], "end_sec": u["end_sec"], "knowledge_unit_refs": [u["unit_id"]],
               "clean_source_refs": u["clean_source_refs"], "raw_source_refs": u["raw_source_refs"], "content": u["content"]} for i, u in enumerate(all_units)]
    (corpus / "corpus_chunks.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in chunks), encoding="utf-8")
    (corpus / "README.md").write_text("# Agent Corpus\n\n读取顺序：CHANNEL_MAP.md → TOPIC_INDEX.md → knowledge_units.jsonl；需要核查时回溯 videos/<id>/clean/transcript.cleaned.md，再回到 transcript/canonical.json。\n", encoding="utf-8")
    return {"videos_total": len(rows), "videos_included": included, "knowledge_units": len(all_units), "topics": len(topics)}


def agent_corpus_gate(root: Path, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = rows if rows is not None else load_catalog(root)
    accessible = [r for r in rows if str(r.get("extraction_status")) in {"TRANSCRIPT_QA_PASSED", "CONTENT_QA_PASSED", "CLEAN_QA_PASSED"}]
    included = sum(1 for r in accessible if (root / "videos" / str(r["video_id"]) / "knowledge" / "knowledge_qa.json").exists())
    terminal = sum(1 for r in rows if str(r.get("extraction_status")) in {"PRIVATE", "DELETED", "UNAVAILABLE"})
    status = "WAITING_FOR_INPUT" if not rows else ("PASS" if included == len(accessible) and len(accessible) + terminal == len(rows) and (root / "agent_corpus" / "README.md").exists() else "FAIL")
    return {"gate": "AGENT_CORPUS", "status": status, "accessible": len(accessible), "included": included}
