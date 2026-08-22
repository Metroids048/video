"""Resumable YouTube transcript -> visual -> content corpus pipeline.

The module deliberately keeps extraction deterministic and provenance-first.  It
reuses M2 transcripts, extracts frames only from locally available media, and
records explicit unavailable/retryable states when a source cannot be acquired.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .storage import load_catalog, load_channel, update_video_state


TRIGGER_TERMS = (
    "这里", "这个位置", "你看", "图中", "这根K线", "这根K", "这条线", "突破",
    "回踩", "高点", "低点", "前高", "前低", "支撑", "压力", "趋势线", "均线",
    "止损", "止盈", "入场", "出场", "背离", "形态", "画线",
)
NUMBER_RE = re.compile(r"(?:\d+(?:\.\d+)?\s*(?:%|倍|点|万|亿)?|\b(?:1m|5m|15m|30m|1h|4h|日线|周线)\b)", re.I)
CONDITION_TERMS = ("如果", "只有", "除非", "当", "但是", "否则", "前提")
TOPIC_TERMS = {
    "支撑压力": ("支撑", "压力"), "趋势": ("趋势", "趋势线"), "K线": ("K线", "K"),
    "突破回踩": ("突破", "回踩"), "风险管理": ("风险", "止损", "止盈", "仓位"),
    "交易心理": ("情绪", "心理", "纪律", "害怕", "恐惧"), "技术指标": ("均线", "指标", "背离"),
    "市场展望": ("市场", "行情", "牛市", "熊市"), "交易系统": ("交易系统", "规则", "复盘"),
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _segments(canonical: dict[str, Any]) -> list[dict[str, Any]]:
    return [s for s in canonical.get("segments", []) if isinstance(s, dict) and s.get("text")]


def _duration(row: dict[str, Any], canonical: dict[str, Any]) -> float:
    value = row.get("duration")
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            pass
    return max((float(s.get("end", 0)) for s in _segments(canonical)), default=0.0)


def _select_timestamps(row: dict[str, Any], canonical: dict[str, Any]) -> list[dict[str, Any]]:
    segments = _segments(canonical)
    duration = _duration(row, canonical)
    candidates: dict[float, dict[str, Any]] = {}
    for segment in segments:
        text = str(segment.get("text", ""))
        reasons: list[str] = []
        if any(term in text for term in TRIGGER_TERMS):
            reasons.append("TRANSCRIPT_TRIGGER")
            if any(term in text for term in ("支撑", "压力", "突破", "回踩")):
                reasons.append("SUPPORT_RESISTANCE")
        if NUMBER_RE.search(text):
            reasons.append("NUMBER_OR_PARAMETER")
        if not reasons:
            continue
        ts = max(0.0, float(segment.get("start", 0)))
        key = round(ts, 1)
        item = candidates.setdefault(key, {"timestamp": ts, "reason": [], "transcript_refs": []})
        item["reason"] = sorted(set(item["reason"]) | set(reasons))
        item["transcript_refs"].append(segment.get("segment_id"))
    step = 75.0
    if duration > 0:
        t = 0.0
        while t < duration:
            key = round(t, 1)
            item = candidates.setdefault(key, {"timestamp": t, "reason": [], "transcript_refs": []})
            item["reason"] = sorted(set(item["reason"]) | {"SAFETY_SAMPLE"})
            t += step
    selected = sorted(candidates.values(), key=lambda x: x["timestamp"])
    # Keep the corpus bounded; preserve all trigger frames, then safety samples.
    if len(selected) > 48:
        trigger = [x for x in selected if x["reason"] != ["SAFETY_SAMPLE"]]
        safety = [x for x in selected if x["reason"] == ["SAFETY_SAMPLE"]]
        selected = sorted(trigger + safety[: max(0, 48 - len(trigger))], key=lambda x: x["timestamp"])
    return selected


def _media_candidates(video_root: Path, video_id: str) -> list[Path]:
    media = video_root / "media"
    if not media.exists():
        return []
    candidates = [p for p in media.glob(f"{video_id}.*") if p.is_file() and p.suffix.lower() not in {".json", ".txt", ".vtt"}]
    priority = {".mp4": 0, ".webm": 1, ".mkv": 2, ".mov": 3, ".m4v": 4, ".wav": 10, ".m4a": 11, ".mp3": 12}
    return sorted(candidates, key=lambda p: (priority.get(p.suffix.lower(), 20), "audio" in p.stem.lower(), p.name))


def _extract_frames(video_root: Path, row: dict[str, Any], canonical: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    visual = video_root / "visual"
    visual.mkdir(parents=True, exist_ok=True)
    keyframes_path = visual / "keyframes.jsonl"
    existing = []
    if keyframes_path.exists():
        for line in keyframes_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing.append(json.loads(line))
    media = _media_candidates(video_root, str(row["video_id"]))
    timestamps = _select_timestamps(row, canonical)
    if not media:
        payload = [{**item, "frame_id": f"F{i:04d}", "video_id": row["video_id"], "path": None,
                    "status": "MEDIA_UNAVAILABLE"} for i, item in enumerate(timestamps, 1)]
        _write_text(keyframes_path, "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in payload))
        return payload, "MEDIA_UNAVAILABLE"
    source = media[0]
    frames: list[dict[str, Any]] = []
    for i, item in enumerate(timestamps, 1):
        frame_id = f"F{i:04d}"
        out = visual / f"frame_{i:04d}.jpg"
        if not out.exists():
            command = ["ffmpeg", "-y", "-ss", f"{item['timestamp']:.3f}", "-i", str(source), "-frames:v", "1",
                       "-q:v", "3", str(out)]
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=120, shell=False)
                if result.returncode != 0 or not out.exists():
                    continue
            except (OSError, subprocess.TimeoutExpired):
                continue
        rel = out.relative_to(video_root).as_posix()
        frames.append({"frame_id": frame_id, "video_id": row["video_id"], "timestamp": item["timestamp"],
                       "reason": item["reason"], "transcript_refs": item["transcript_refs"], "path": rel,
                       "status": "EXTRACTED"})
    _write_text(keyframes_path, "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in frames))
    if frames:
        # A lightweight contact sheet is useful to agents without requiring vision calls.
        sheet = visual / "contact_sheet.jpg"
        if not sheet.exists():
            inputs = [str(visual / Path(x["path"]).name) for x in frames]
            command = ["ffmpeg", "-y"]
            for path in inputs:
                command += ["-i", path]
            n = len(inputs)
            command += ["-filter_complex", f"tile={min(4, n)}x{math.ceil(n / min(4, n))}:padding=4:margin=4",
                        "-q:v", "4", str(sheet)]
            try:
                subprocess.run(command, capture_output=True, text=True, timeout=180, shell=False)
            except (OSError, subprocess.TimeoutExpired):
                pass
    return frames, "PASS" if frames else "FRAME_EXTRACTION_FAILED"


def _visual_evidence(video_root: Path, row: dict[str, Any], frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for frame in frames:
        if frame.get("status") != "EXTRACTED":
            continue
        reasons = frame.get("reason", [])
        scene = "TRADING_CHART" if any(x in reasons for x in ("SUPPORT_RESISTANCE", "TRANSCRIPT_TRIGGER")) else "UNKNOWN"
        evidence.append({"frame_id": frame["frame_id"], "timestamp": frame["timestamp"], "scene_type": scene,
                         "visible_text": [], "instruments": [], "timeframes": [], "indicators": [],
                         "price_levels": [], "trend_lines": [], "zones": [], "annotations": [],
                         "chart_patterns": [], "speaker_reference": None,
                         "visual_explanation": "画面已保存；未调用视觉模型，具体图表元素需人工/Agent复核。",
                         "confidence": 0.25, "uncertainty": ["NO_VISION_MODEL"], "frame_refs": [frame["frame_id"]]})
    _write_text(video_root / "visual" / "visual_evidence.jsonl", "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in evidence))
    return evidence


def _semantic_units(video_root: Path, row: dict[str, Any], canonical: dict[str, Any], frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments = _segments(canonical)
    units: list[dict[str, Any]] = []
    for index, segment in enumerate(segments, 1):
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        topic = next((name for name, terms in TOPIC_TERMS.items() if any(term in text for term in terms)), "一般讲解")
        typ = "WARNING" if any(x in text for x in ("风险", "注意", "不要", "不安全")) else "EXPLANATION"
        if any(x in text for x in ("例如", "案例", "比如")):
            typ = "EXAMPLE"
        if any(x in text for x in ("定义", "是指", "意味着")):
            typ = "DEFINITION"
        refs = [f["frame_id"] for f in frames if abs(float(f["timestamp"]) - float(segment.get("start", 0))) <= 8 or
                any(r in f.get("transcript_refs", []) for r in [segment.get("segment_id")])]
        unit = {"unit_id": f"U{index:04d}", "video_id": row["video_id"], "start_sec": segment.get("start", 0),
                "end_sec": segment.get("end", 0), "topic": topic, "type": typ, "speaker_content": text,
                "conditions": [text] if any(x in text for x in CONDITION_TERMS) else [], "exceptions": [],
                "numbers": NUMBER_RE.findall(text), "instruments": [], "timeframes": [], "examples": [],
                "risks": [text] if typ == "WARNING" else [], "visual_dependency": bool(refs) or any(x in text for x in TRIGGER_TERMS),
                "frame_refs": refs, "transcript_segment_refs": [segment.get("segment_id")], "confidence": 0.7,
                "uncertainty": ["ASR_TEXT_MAY_CONTAIN_ERRORS"]}
        units.append(unit)
    path = video_root / "semantic_units.jsonl"
    _write_text(path, "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in units))
    return units


def _content_and_map(video_root: Path, row: dict[str, Any], canonical: dict[str, Any], units: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    title = row.get("title") or row["video_id"]
    lines = [f"# {title}", "", "## 基本信息", "", f"Video ID: {row['video_id']}",
             f"发布时间: {row.get('published_at') or 'UNKNOWN'}", f"时长: {row.get('duration') or 'UNKNOWN'} sec",
             f"Source: {canonical.get('source_type', 'UNKNOWN')}", "Transcript QA: PASS",
             f"Visual QA: {'PASS' if evidence else 'UNAVAILABLE'}", "", "## 内容导航", "",
             "以下正文按原始 transcript segment 保留，并附带时间戳与来源；不是摘要。", "", "## 逐段内容", ""]
    source_map: list[dict[str, Any]] = []
    for unit in units:
        start = float(unit["start_sec"]); end = float(unit["end_sec"])
        def fmt(sec: float) -> str:
            return f"{int(sec // 60):02d}:{int(sec % 60):02d}"
        refs = unit.get("frame_refs", [])
        lines += [f"### {fmt(start)} - {fmt(end)}", "", unit["speaker_content"], "", "Source:",
                  f"Transcript segments: {', '.join(unit['transcript_segment_refs'])}",
                  f"Frames: {', '.join(refs) if refs else 'NONE'}", ""]
        source_map.append({"content_ref": f"C{len(source_map)+1:04d}", "semantic_unit": unit["unit_id"],
                           "video_id": row["video_id"], "start": start, "end": end,
                           "transcript_refs": unit["transcript_segment_refs"], "frame_refs": refs})
    lines += ["## 关键概念与定义", "", "仅列出 transcript 中出现的主题标签，不扩写为交易规则。", ""]
    for topic in sorted({u["topic"] for u in units}):
        lines.append(f"- {topic}")
    lines += ["", "## 图表/视觉讲解", ""]
    for item in evidence:
        lines += [f"Frame {item['frame_id']} ({item['timestamp']:.1f}s): {item['visual_explanation']}", ""]
    lines += ["## 条件与前提", "", "保留在逐段内容中；未从原话推导新条件。", "", "## 例外与限制", "",
              "未明确表达的内容不作推断。", "", "## 不确定内容", "", "ASR 不确定：见 semantic_units.jsonl 的 uncertainty。",
              "", "视觉不确定：NO_VISION_MODEL；画面仅作为证据帧保存。", ""]
    (video_root / "content.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _write_json(video_root / "source_map.json", source_map)
    return {"content_refs": len(source_map), "source_map_refs": len(source_map)}


def _qa(video_root: Path, canonical: dict[str, Any], units: list[dict[str, Any]], frames: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    text = str(canonical.get("text", ""))
    numbers = NUMBER_RE.findall(text)
    content = (video_root / "content.md").read_text(encoding="utf-8") if (video_root / "content.md").exists() else ""
    missing_numbers = [n for n in numbers if n not in content]
    visual_deps = sum(1 for u in units if u.get("visual_dependency"))
    reasons: list[str] = []
    if not units or not content.strip(): reasons.append("EMPTY_EXTRACTION")
    if missing_numbers: reasons.append("NUMBER_PRESERVATION_FAIL")
    if visual_deps and not frames: reasons.append("FAIL_VISUAL_EVIDENCE_MISSING")
    status = "PASS" if not reasons else "FAIL"
    payload = {"status": status, "reasons": reasons, "transcript_status": "PASS",
               "semantic_unit_count": len(units), "frame_count": len(frames), "visual_evidence_count": len(evidence),
               "number_count": len(numbers), "missing_numbers": missing_numbers, "source_map_present": (video_root / "source_map.json").exists(),
               "generated_at": _now()}
    _write_json(video_root / "qa.json", payload)
    return payload


def process_video(root: Path, row: dict[str, Any], *, resume: bool = True) -> dict[str, Any]:
    video_id = str(row["video_id"]); video_root = root / "videos" / video_id
    qa_path = video_root / "qa.json"
    prior = _read_json(qa_path, {}) or {}
    if resume and prior.get("status") == "PASS":
        return {"video_id": video_id, "status": "SKIPPED", "reason": "CONTENT_QA_PASSED"}
    canonical_path = video_root / "transcript" / "canonical.json"
    transcript_qa = _read_json(video_root / "transcript" / "qa.json", {}) or {}
    if not canonical_path.exists() or transcript_qa.get("status") not in {"PASS", "WARN"}:
        try:
            from .extraction import extract_transcript
            result = extract_transcript(root, video_id, keep_media=True)
            if result.get("status") not in {"PASS", "SKIPPED"}:
                return {"video_id": video_id, "status": result.get("status", "RETRYABLE_FAILED"), "reason": "TRANSCRIPT_NOT_AVAILABLE"}
        except Exception as exc:  # noqa: BLE001 - isolate one inaccessible video
            _append_jsonl(root / "reports" / "failures.jsonl", {"video_id": video_id, "status": "FAILED_RETRYABLE", "stage": "TRANSCRIPT", "error": str(exc), "at": _now()})
            return {"video_id": video_id, "status": "RETRYABLE_FAILED", "reason": "TRANSCRIPT_EXCEPTION"}
        transcript_qa = _read_json(video_root / "transcript" / "qa.json", {}) or {}
        if not canonical_path.exists() or transcript_qa.get("status") not in {"PASS", "WARN"}:
            return {"video_id": video_id, "status": "RETRYABLE_FAILED", "reason": "TRANSCRIPT_QA_NOT_PASSED"}
    canonical = _read_json(canonical_path, {}) or {}
    try:
        frames, frame_status = _extract_frames(video_root, row, canonical)
        evidence = _visual_evidence(video_root, row, frames)
        units = _semantic_units(video_root, row, canonical, frames)
        _content_and_map(video_root, row, canonical, units, evidence)
        qa = _qa(video_root, canonical, units, frames, evidence)
        if frame_status == "MEDIA_UNAVAILABLE" and any(u.get("visual_dependency") for u in units):
            qa["status"] = "UNAVAILABLE"
            qa["reasons"] = ["VISUAL_MEDIA_UNAVAILABLE"]
            _write_json(video_root / "qa.json", qa)
            update_video_state(root, video_id, extraction_status="UNAVAILABLE")
            return {"video_id": video_id, "status": "UNAVAILABLE", **qa}
        if qa["status"] == "PASS":
            update_video_state(root, video_id, extraction_status="CONTENT_QA_PASSED")
            return {"video_id": video_id, "status": "PASS", "frame_status": frame_status, **qa}
        update_video_state(root, video_id, extraction_status="RETRYABLE_FAILED")
        return {"video_id": video_id, "status": "RETRYABLE_FAILED", **qa}
    except Exception as exc:  # noqa: BLE001 - per-video isolation
        _append_jsonl(root / "reports" / "failures.jsonl", {"video_id": video_id, "status": "FAILED_RETRYABLE", "error": str(exc), "at": _now()})
        update_video_state(root, video_id, extraction_status="RETRYABLE_FAILED")
        return {"video_id": video_id, "status": "RETRYABLE_FAILED", "reason": str(exc)}


def _progress(root: Path, rows: list[dict[str, Any]], last_video_id: str | None = None) -> dict[str, Any]:
    counts = Counter(str(r.get("extraction_status", "FAILED_UNKNOWN")) for r in rows)
    payload = {"total": len(rows), "transcript_passed": sum(1 for r in rows if r.get("extraction_status") == "TRANSCRIPT_QA_PASSED"),
               "visual_passed": sum(1 for r in rows if (root / "videos" / str(r["video_id"]) / "visual" / "visual_evidence.jsonl").exists()),
               "content_passed": counts.get("CONTENT_QA_PASSED", 0), "terminal_unavailable": sum(counts.get(x, 0) for x in ("PRIVATE", "DELETED", "UNAVAILABLE", "BLOCKED_BY_YOUTUBE")),
               "retryable_failed": counts.get("RETRYABLE_FAILED", 0), "unknown": counts.get("FAILED_UNKNOWN", 0), "last_video_id": last_video_id, "updated_at": _now()}
    _write_json(root / "reports" / "progress.json", payload)
    return payload


def build_agent_bundle(root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    bundle = root / "agent_bundle"; topics: dict[str, list[dict[str, Any]]] = defaultdict(list); chunks: list[dict[str, Any]] = []
    video_lines = ["# VIDEO_INDEX", ""]
    for row in rows:
        vid = str(row["video_id"]); vroot = root / "videos" / vid; units_path = vroot / "semantic_units.jsonl"
        units = []
        if units_path.exists():
            units = [json.loads(x) for x in units_path.read_text(encoding="utf-8").splitlines() if x.strip()]
        title = row.get("title") or vid
        video_lines.append(f"- **{title}** (`{vid}`) — {row.get('duration') or 'UNKNOWN'} sec — [content](../videos/{vid}/content.md)")
        for unit in units:
            topics[unit["topic"]].append({"video_id": vid, "title": title, "unit": unit})
            chunks.append({"chunk_id": f"{vid}-{unit['unit_id']}", "video_id": vid, "topic": [unit["topic"]], "content": unit["speaker_content"],
                           "start_sec": unit["start_sec"], "end_sec": unit["end_sec"], "semantic_unit_refs": [unit["unit_id"]],
                           "frame_refs": unit.get("frame_refs", []), "source_map_refs": []})
    bundle.mkdir(parents=True, exist_ok=True); (bundle / "topics").mkdir(exist_ok=True)
    (bundle / "VIDEO_INDEX.md").write_text("\n".join(video_lines) + "\n", encoding="utf-8")
    topic_lines = ["# TOPIC_INDEX", ""]
    for topic, items in sorted(topics.items()):
        slug = re.sub(r"[^\w-]+", "-", topic.lower()).strip("-") or "topic"
        topic_lines.append(f"- [{topic}](topics/{slug}.md) ({len(items)} units)")
        body = [f"# {topic}", "", "## 相关视频", ""] + [f"- `{x['video_id']}` {x['title']} @ {x['unit']['start_sec']:.1f}s" for x in items]
        (bundle / "topics" / f"{slug}.md").write_text("\n".join(body) + "\n", encoding="utf-8")
    (bundle / "TOPIC_INDEX.md").write_text("\n".join(topic_lines) + "\n", encoding="utf-8")
    channel = load_channel(root)
    (bundle / "CHANNEL_OVERVIEW.md").write_text(f"# {channel.get('title') or channel.get('handle') or 'YouTube Channel'}\n\n视频数：{len(rows)}\n\n主题索引见 [TOPIC_INDEX.md](TOPIC_INDEX.md)。\n", encoding="utf-8")
    (bundle / "README.md").write_text("# Agent Bundle\n\n先读 CHANNEL_OVERVIEW.md、TOPIC_INDEX.md、VIDEO_INDEX.md；单视频详情读 videos/<id>/content.md。\n", encoding="utf-8")
    (bundle / "catalog.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    _write_text(bundle / "corpus_chunks.jsonl", "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in chunks))
    return {"topics": len(topics), "chunks": len(chunks)}


def run_corpus(root: Path, *, resume: bool = True, video_id: str | None = None) -> dict[str, Any]:
    rows = load_catalog(root)
    if video_id:
        rows = [r for r in rows if r.get("video_id") == video_id]
    root.joinpath("reports").mkdir(parents=True, exist_ok=True)
    _write_json(root / "reports" / "latest-run.json", {"started_at": _now(), "total": len(rows)})
    results = []
    for row in rows:
        results.append(process_video(root, row, resume=resume))
        all_rows = load_catalog(root)
        _progress(root, all_rows, str(row.get("video_id")))
    all_rows = load_catalog(root)
    bundle = build_agent_bundle(root, all_rows)
    statuses = Counter(str(r.get("extraction_status", "FAILED_UNKNOWN")) for r in all_rows)
    terminal = sum(statuses.get(x, 0) for x in ("PRIVATE", "DELETED", "UNAVAILABLE", "BLOCKED_BY_YOUTUBE"))
    content = statuses.get("CONTENT_QA_PASSED", 0)
    payload = {"total": len(all_rows), "content_passed": content, "terminal_unavailable": terminal,
               "failed_unknown": statuses.get("FAILED_UNKNOWN", 0), "retryable_failed": statuses.get("RETRYABLE_FAILED", 0), "bundle": bundle,
               "generated_at": _now(), "pass": content + terminal == len(all_rows) and statuses.get("FAILED_UNKNOWN", 0) == 0 and statuses.get("RETRYABLE_FAILED", 0) == 0}
    _write_json(root / "reports" / "corpus-final.json", payload)
    return payload


def corpus_status(root: Path) -> dict[str, Any]:
    rows = load_catalog(root); statuses = Counter(str(r.get("extraction_status", "FAILED_UNKNOWN")) for r in rows)
    return {"total": len(rows), "statuses": dict(statuses), "progress": _read_json(root / "reports" / "progress.json", {}), "final": _read_json(root / "reports" / "corpus-final.json", {})}


def finalize_corpus(root: Path, *, sample_size: int = 20) -> dict[str, Any]:
    """Write human/agent-facing closure reports without touching source media."""
    rows = load_catalog(root)
    rows = sorted(rows, key=lambda r: str(r.get("video_id")))
    sample = rows[: min(sample_size, len(rows))]
    sample_items = []
    for row in sample:
        vid = str(row["video_id"]); vroot = root / "videos" / vid
        qa = _read_json(vroot / "qa.json", {}) or {}
        sample_items.append({"video_id": vid, "status": row.get("extraction_status"), "qa_status": qa.get("status"),
                             "content_present": (vroot / "content.md").exists(),
                             "semantic_units_present": (vroot / "semantic_units.jsonl").exists(),
                             "source_map_present": (vroot / "source_map.json").exists(),
                             "visual_evidence_present": (vroot / "visual" / "visual_evidence.jsonl").exists()})
    sample_report = {"sampled": len(sample_items), "passed": sum(1 for x in sample_items if x["qa_status"] == "PASS"),
                     "issues": [x for x in sample_items if x["qa_status"] not in {None, "PASS"}], "items": sample_items,
                     "generated_at": _now()}
    _write_json(root / "reports" / "sample-audit.json", sample_report)
    statuses = Counter(str(r.get("extraction_status", "FAILED_UNKNOWN")) for r in rows)
    content_count = statuses.get("CONTENT_QA_PASSED", 0)
    terminal_count = sum(statuses.get(x, 0) for x in ("PRIVATE", "DELETED", "UNAVAILABLE", "BLOCKED_BY_YOUTUBE"))
    total_units = 0; total_frames = 0; total_maps = 0
    for row in rows:
        vroot = root / "videos" / str(row["video_id"])
        up = vroot / "semantic_units.jsonl"
        if up.exists(): total_units += sum(1 for line in up.read_text(encoding="utf-8").splitlines() if line.strip())
        kp = vroot / "visual" / "keyframes.jsonl"
        if kp.exists(): total_frames += sum(1 for line in kp.read_text(encoding="utf-8").splitlines() if line.strip())
        sm = _read_json(vroot / "source_map.json", []) or []
        total_maps += len(sm) if isinstance(sm, list) else 0
    coverage = ["# Corpus Coverage", "", f"- Total videos: {len(rows)}", f"- CONTENT_QA_PASSED: {content_count}",
                f"- Terminal unavailable/blocked: {terminal_count}", f"- FAILED_UNKNOWN: {statuses.get('FAILED_UNKNOWN', 0)}",
                f"- Retryable failed: {statuses.get('RETRYABLE_FAILED', 0)}", f"- Semantic units: {total_units}",
                f"- Keyframes: {total_frames}", f"- Source maps: {total_maps}", "", "Only content QA passed videos have information-preserving content; terminal videos retain explicit catalog state and failure provenance."]
    (root / "reports" / "coverage.md").write_text("\n".join(coverage) + "\n", encoding="utf-8")
    channel = load_channel(root)
    (root / "README_FOR_AGENTS.md").write_text(
        f"# {channel.get('title') or channel.get('handle') or 'YouTube Corpus'}\n\n"
        "先读 `agent_bundle/CHANNEL_OVERVIEW.md`、`agent_bundle/TOPIC_INDEX.md`、`agent_bundle/VIDEO_INDEX.md`。\n"
        "单视频详情读 `videos/<video_id>/content.md`；原话读 `videos/<video_id>/transcript/transcript.md`；\n"
        "时间戳细节读 `semantic_units.jsonl` 与 `source_map.json`；画面证据读 `visual/`。\n\n"
        "本目录是可恢复的研究语料 workspace，不应提交 Git。\n", encoding="utf-8")
    return sample_report
