"""Deterministic, provenance-first transcript cleaning for trading ASR text."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from .storage import load_catalog


NEGATION_TERMS = ("不", "不能", "不要", "没有", "除非", "只有", "才", "否则", "但是")
CRITICAL_TERMS = (
    "前高", "前低", "突破", "跌破", "做多", "做空", "止损", "止盈", "盈亏比",
    "周期", "级别", "入场", "出场", "不", "不能", "不要", "除非", "只有",
)
TIMEFRAME_RE = re.compile(r"(?:\d+\s*[mMhHdD]|\d+\s*分钟|\d+\s*小时|日线|周线|月线)")
NUMBER_RE = re.compile(r"(?<![A-Za-z])(?:\d+(?:\.\d+)?|\d{1,3}(?:,\d{3})+)(?:\s*(?:%|倍|点|万|亿))?(?![A-Za-z])")
SUSPICIOUS_ASR_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("MALFORMED_LATIN_TOKEN", re.compile(r"裸\s*[kK]\s*[sS]\s*[bB]")),
    ("LIKELY_ASR_TERM", re.compile(r"航行分析课|关键为|供品上扣|仓卫(?:视水)?|备持备离|应亏笔|可负之性")),
)
FILLER_TERMS = ("对吧", "然后", "这个", "好吧", "能理解", "你看")
FILLER_THRESHOLD = 12

# Conservative aliases observed in the corpus. Context decides whether a replacement is safe.
ASR_ALIASES: dict[str, dict[str, Any]] = {
    "钱高": {"canonical_term": "前高", "context_terms": ("突破", "趋势", "高点", "低点", "前低"), "confidence": 0.96},
    "钱低": {"canonical_term": "前低", "context_terms": ("突破", "趋势", "高点", "低点", "前高"), "confidence": 0.96},
    "道士理论": {"canonical_term": "道氏理论", "context_terms": ("道氏", "趋势", "123法则", "理论"), "confidence": 0.99},
    "道士": {"canonical_term": "道氏", "context_terms": ("理论", "趋势", "123法则"), "confidence": 0.92},
    "斜拨": {"canonical_term": "谐波", "context_terms": ("AB=CD", "蝴蝶", "螃蟹", "形态"), "confidence": 0.94},
    "指营": {"canonical_term": "止盈", "context_terms": ("止损", "盈亏比", "出场", "利润"), "confidence": 0.98},
    "回彻": {"canonical_term": "回撤", "context_terms": ("斐波那契", "支撑", "压力", "趋势"), "confidence": 0.94},
    "肺胖大气": {"canonical_term": "斐波那契", "context_terms": ("回撤", "支撑", "压力", "0.382", "0.618"), "confidence": 0.99},
    "斐波纳气": {"canonical_term": "斐波那契", "context_terms": ("回撤", "支撑", "压力", "0.382", "0.618"), "confidence": 0.99},
    "芬麻切": {"canonical_term": "斐波那契", "context_terms": ("回撤", "支撑", "压力", "0.382", "0.618"), "confidence": 0.90},
}


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_text(text: str) -> str:
    """Normalize typography without flattening meaningful ASCII tokens."""
    value = unicodedata.normalize("NFKC", str(text or ""))
    value = value.replace("\u00a0", " ").replace("\u3000", " ")
    value = re.sub(r"[ \t]+", " ", value)
    # Join split Chinese words, units and numeric fragments conservatively.
    value = re.sub(r"(?<=[\u4e00-\u9fff])[ ]+(?=[\u4e00-\u9fff])", "", value)
    value = re.sub(r"(?<=\d)[ ]+(?=[mMhHdD]\b)", "", value)
    value = re.sub(r"(?<=\d)[ ]+(?=[\u4e00-\u9fff])", "", value)
    value = re.sub(r"(?<=[\u4e00-\u9fff])[ ]+(?=\d)", "", value)
    value = re.sub(r"(?<!\d)(\d)\.[ ]*(\d)[ ]*(\d)[ ]*(\d)(?=[ ]*[\u4e00-\u9fff])", r"\1.\2\3\4", value)
    value = re.sub(r"(?<!\d)(\d)\.[ ]*(\d)[ ]*(\d)(?!\d)", r"\1.\2\3", value)
    value = re.sub(r"(?<!\d)(\d)[ ]+(\d)[ ]+(\d)(?=[ ]*法则)", r"\1\2\3", value)
    value = re.sub(r"(\d)[ ]*,[ ]*(\d{3}\b)", r"\1,\2", value)
    value = re.sub(r"[ ]+([，。！？；：、）】》])", r"\1", value)
    value = re.sub(r"([（【《])[ ]+", r"\1", value)
    value = re.sub(r"[ \t]*\n[ \t]*", " ", value)
    return value.strip()


def semantic_suspects(text: str) -> list[dict[str, Any]]:
    """Find high-signal ASR/noise patterns that require human or audio review."""
    issues: list[dict[str, Any]] = []
    for code, pattern in SUSPICIOUS_ASR_PATTERNS:
        match = pattern.search(text)
        if match:
            issues.append({"code": code, "evidence": match.group(0), "severity": "REVIEW_REQUIRED"})
    filler_count = sum(text.count(term) for term in FILLER_TERMS)
    if filler_count >= FILLER_THRESHOLD:
        issues.append({"code": "EXCESSIVE_SPOKEN_FILLER", "count": filler_count, "severity": "REVIEW_REQUIRED"})
    return issues


def _context_score(alias: str, title: str, previous: str, current: str, following: str) -> tuple[float, str]:
    data = ASR_ALIASES[alias]
    context = " ".join((title, previous, current, following))
    hits = sum(1 for term in data["context_terms"] if term in context)
    title_hits = sum(1 for term in data["context_terms"] if term in title)
    if hits == 0:
        return 0.0, "UNRESOLVED_CONTEXT"
    score = min(0.999, float(data["confidence"]) + min(0.03, title_hits * 0.01))
    return score, "TITLE_CONTEXT" if title_hits else "LEXICON_CONTEXT"


def clean_segment(*, video_id: str, title: str, segment: dict[str, Any], previous: str = "", following: str = "") -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    original = str(segment.get("text", ""))
    cleaned = normalize_text(original)
    corrections: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for alias, data in ASR_ALIASES.items():
        if alias not in cleaned:
            continue
        score, method = _context_score(alias, title, previous, cleaned, following)
        if score >= 0.90:
            cleaned = cleaned.replace(alias, str(data["canonical_term"]))
            corrections.append({"from": alias, "to": data["canonical_term"], "type": "DOMAIN_TERM", "confidence": score})
        else:
            unresolved.append({"term": alias, "candidate": data["canonical_term"], "reason": method, "critical": alias in CRITICAL_TERMS})
    result = dict(segment)
    result["text"] = cleaned
    result["raw_segment_id"] = segment.get("segment_id")
    result["clean_version"] = "deterministic-v1"
    mapping = None
    if original != cleaned or corrections:
        mapping = {"video_id": video_id, "segment_id": segment.get("segment_id"), "original": original,
                   "cleaned": cleaned, "corrections": corrections, "method": "NFKC+LEXICON_CONTEXT",
                   "source_preserved": True}
    return result, mapping, (unresolved[0] if unresolved else None)


def _polarity_tokens(text: str) -> list[str]:
    return [term for term in NEGATION_TERMS if term in text]


def clean_video(root: Path, row: dict[str, Any], *, resume: bool = True) -> dict[str, Any]:
    video_id = str(row["video_id"])
    vroot = root / "videos" / video_id
    clean_root = vroot / "clean"
    qa_path = clean_root / "clean_qa.json"
    if resume and qa_path.exists():
        prior = _read_json(qa_path, {}) or {}
        if prior.get("status") == "CLEAN_QA_PASSED" and prior.get("semantic_status") == "PASS":
            return {"video_id": video_id, "status": "SKIPPED", **prior}
    canonical_path = vroot / "transcript" / "canonical.json"
    canonical = _read_json(canonical_path, {}) or {}
    transcript_qa = _read_json(vroot / "transcript" / "qa.json", {}) or {}
    if not canonical_path.exists() or transcript_qa.get("status") not in {"PASS", "WARN"}:
        return {"video_id": video_id, "status": "WAITING_FOR_INPUT", "reason": "TRANSCRIPT_QA_NOT_PASSED"}
    segments = [s for s in canonical.get("segments", []) if isinstance(s, dict) and s.get("text")]
    cleaned_segments: list[dict[str, Any]] = []
    maps: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    semantic_issues: list[dict[str, Any]] = []
    for index, segment in enumerate(segments):
        previous = str(segments[index - 1].get("text", "")) if index else ""
        following = str(segments[index + 1].get("text", "")) if index + 1 < len(segments) else ""
        clean, mapping, unknown = clean_segment(video_id=video_id, title=str(row.get("title") or ""), segment=segment,
                                                 previous=previous, following=following)
        cleaned_segments.append(clean)
        if mapping:
            maps.append(mapping)
        if unknown:
            unresolved.append({"video_id": video_id, "segment_id": segment.get("segment_id"), **unknown})
        for issue in semantic_suspects(str(clean.get("text", ""))):
            semantic_issues.append({"video_id": video_id, "segment_id": segment.get("segment_id"), **issue})
    raw_text = str(canonical.get("text") or " ".join(str(s.get("text", "")) for s in segments))
    cleaned_text = " ".join(str(s.get("text", "")) for s in cleaned_segments)
    raw_numbers = sorted(set(NUMBER_RE.findall(normalize_text(raw_text))))
    clean_numbers = sorted(set(NUMBER_RE.findall(cleaned_text)))
    missing_numbers = [n for n in raw_numbers if n not in clean_numbers]
    # Compare polarity after the same whitespace normalization; ASR commonly
    # splits 否/则、只/有 and similar compounds across tokens.
    polarity_changed = sorted(_polarity_tokens(normalize_text(raw_text))) != sorted(_polarity_tokens(normalize_text(cleaned_text)))
    critical_unresolved = [x for x in unresolved if x.get("critical")]
    status = "CLEAN_QA_PASSED" if not missing_numbers and not polarity_changed and not critical_unresolved and not semantic_issues else "CLEAN_QA_FAILED"
    cleaned = {"video_id": video_id, "source_type": canonical.get("source_type"), "raw_transcript": "transcript/canonical.json",
               "clean_version": "deterministic-v1", "text": cleaned_text, "segments": cleaned_segments}
    _write_json(clean_root / "cleaned.json", cleaned)
    lines = [f"# {row.get('title') or video_id}", "", f"Video ID: {video_id}", "Clean version: deterministic-v1", "Raw source: transcript/transcript.md", "", "## Transcript", ""]
    for segment in cleaned_segments:
        start, end = float(segment.get("start", 0)), float(segment.get("end", 0))
        lines.extend([f"### {int(start // 3600):02d}:{int(start % 3600 // 60):02d}:{int(start % 60):02d} - {int(end // 3600):02d}:{int(end % 3600 // 60):02d}:{int(end % 60):02d}", "", str(segment.get("text", "")), ""])
    clean_root.mkdir(parents=True, exist_ok=True)
    (clean_root / "transcript.cleaned.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (clean_root / "correction_map.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in maps), encoding="utf-8")
    (clean_root / "unresolved.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in unresolved), encoding="utf-8")
    (clean_root / "semantic_review.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in semantic_issues), encoding="utf-8")
    qa = {"status": status, "raw_segment_count": len(segments), "clean_segment_count": len(cleaned_segments),
          "source_mapping_complete": len(cleaned_segments) == len(segments) and all(s.get("raw_segment_id") for s in cleaned_segments),
          "numbers_preserved": not missing_numbers, "missing_numbers": missing_numbers,
          "critical_terms_checked": True, "polarity_preserved": not polarity_changed,
          "unresolved_count": len(unresolved), "critical_unresolved_count": len(critical_unresolved),
          "correction_count": len(maps), "semantic_status": "PASS" if not semantic_issues else "REVIEW_REQUIRED",
          "semantic_issue_count": len(semantic_issues)}
    _write_json(qa_path, qa)
    return {"video_id": video_id, "status": status, **qa}


def clean_corpus_gate(root: Path, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = rows if rows is not None else load_catalog(root)
    accessible = [r for r in rows if str(r.get("extraction_status")) in {"TRANSCRIPT_QA_PASSED", "CONTENT_QA_PASSED", "CLEAN_QA_PASSED"}]
    passed = 0
    unresolved_critical = 0
    for row in accessible:
        qa = _read_json(root / "videos" / str(row["video_id"]) / "clean" / "clean_qa.json", {}) or {}
        passed += qa.get("status") == "CLEAN_QA_PASSED" and qa.get("semantic_status") == "PASS"
        unresolved_critical += int(qa.get("critical_unresolved_count", 0) or 0)
    terminal = sum(1 for r in rows if str(r.get("extraction_status")) in {"PRIVATE", "DELETED", "UNAVAILABLE"})
    semantic_review_required = sum(
        int((_read_json(root / "videos" / str(r["video_id"]) / "clean" / "clean_qa.json", {}) or {}).get("semantic_issue_count", 0) or 0)
        for r in accessible
    )
    status = "WAITING_FOR_INPUT" if not rows else ("PASS" if len(accessible) == passed and unresolved_critical == 0 and semantic_review_required == 0 and len(accessible) + terminal == len(rows) else "FAIL")
    return {"gate": "CLEAN_CORPUS", "status": status, "total": len(rows), "accessible": len(accessible),
            "clean_qa_passed": passed, "critical_unresolved": unresolved_critical,
            "semantic_review_required": semantic_review_required}


def plan_local_audio_repair(root: Path, video_id: str, segment_id: str, *, window_sec: int = 30, model: str = "large-v3") -> dict[str, Any]:
    """Return a bounded local re-transcription plan for one unresolved segment.

    Planning is side-effect free; callers may execute it only after a critical
    unresolved item is confirmed.  It never schedules a full-video rerun.
    """
    if not 20 <= window_sec <= 60:
        raise ValueError("局部 audio repair window 必须在 20–60 秒")
    if model != "large-v3":
        raise ValueError("关键规则片段的局部 repair 固定使用 large-v3")
    canonical = _read_json(root / "videos" / video_id / "transcript" / "canonical.json", {}) or {}
    segment = next((s for s in canonical.get("segments", []) if str(s.get("segment_id")) == segment_id), None)
    if not segment:
        return {"status": "NOT_FOUND", "video_id": video_id, "segment_id": segment_id}
    media_dir = root / "videos" / video_id / "media"
    media = next((p for p in media_dir.glob(f"{video_id}.*") if p.is_file() and p.suffix.lower() not in {".json", ".txt"}), None)
    start = max(0.0, float(segment.get("start", 0)) - window_sec / 2)
    end = float(segment.get("end", 0)) + window_sec / 2
    return {"status": "READY" if media else "MEDIA_UNAVAILABLE", "video_id": video_id, "segment_id": segment_id,
            "media": str(media.relative_to(root)) if media else None, "start_sec": start, "end_sec": end,
            "model": model, "scope": "LOCAL_WINDOW_ONLY", "full_video_rerun": False}
