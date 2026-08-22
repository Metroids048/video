"""Canonical transcript representation and deterministic subtitle normalization."""
from __future__ import annotations

import html
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class TranscriptSegment:
    segment_id: str
    start: float
    end: float
    text: str


@dataclass
class TranscriptWord:
    text: str
    start: float
    end: float
    type: str = "word"
    speaker_id: str | None = None


@dataclass
class CanonicalTranscript:
    schema_version: str
    video_id: str
    language: str
    source_type: str
    provider: str
    generated_at: str
    text: str
    segments: list[TranscriptSegment] = field(default_factory=list)
    words: list[TranscriptWord] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["segments"] = [asdict(item) for item in self.segments]
        payload["words"] = [asdict(item) for item in self.words]
        return payload


_TIMESTAMP = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{3})")


def parse_timestamp(value: str) -> float:
    match = _TIMESTAMP.search(value.strip())
    if not match:
        raise ValueError(f"invalid subtitle timestamp: {value!r}")
    hours, minutes, seconds, millis = match.groups()
    return float(hours or 0) * 3600 + float(minutes) * 60 + float(seconds) + float(millis) / 1000


def _clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", html.unescape(value))
    value = value.replace("\ufeff", "").replace("\\N", " ")
    return re.sub(r"\s+", " ", value).strip()


def parse_vtt(text: str) -> tuple[str | None, list[TranscriptSegment]]:
    """Parse WebVTT/SRT-like cues while preserving source timestamps."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    language: str | None = None
    segments: list[TranscriptSegment] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if line.upper().startswith("WEBVTT"):
            language_match = re.search(r"LANGUAGE[=: ]+([A-Za-z-]+)", line, re.I)
            language = language_match.group(1) if language_match else language
            index += 1
            continue
        if "-->" not in line:
            index += 1
            continue
        left, right = [part.strip() for part in line.split("-->", 1)]
        right = right.split()[0]
        try:
            start, end = parse_timestamp(left), parse_timestamp(right)
        except ValueError:
            index += 1
            continue
        index += 1
        body: list[str] = []
        while index < len(lines) and lines[index].strip():
            body.append(lines[index].strip())
            index += 1
        value = _clean_text(" ".join(body))
        if value and end >= start:
            segments.append(TranscriptSegment(f"SEG_{len(segments) + 1:04d}", start, end, value))
        index += 1
    return language, segments


def _segments_from_words(words: list[TranscriptWord]) -> list[TranscriptSegment]:
    result: list[TranscriptSegment] = []
    current: list[TranscriptWord] = []
    for word in words:
        if word.type != "word":
            continue
        if current and word.start - current[-1].end > 1.2:
            result.append(TranscriptSegment(f"SEG_{len(result) + 1:04d}", current[0].start, current[-1].end,
                                             " ".join(item.text for item in current)))
            current = []
        current.append(word)
    if current:
        result.append(TranscriptSegment(f"SEG_{len(result) + 1:04d}", current[0].start, current[-1].end,
                                        " ".join(item.text for item in current)))
    return result


def canonical_from_captions(video_id: str, *, language: str, source_type: str, provider: str,
                            segments: Iterable[TranscriptSegment], provenance: dict[str, Any] | None = None) -> CanonicalTranscript:
    normalized: list[TranscriptSegment] = []
    for index, segment in enumerate(segments, 1):
        start = max(0.0, float(segment.start))
        end = max(start, float(segment.end))
        text = _clean_text(segment.text)
        if text:
            normalized.append(TranscriptSegment(f"SEG_{index:04d}", start, end, text))
    return CanonicalTranscript("1.0", video_id, language, source_type, provider, _now(),
                               " ".join(item.text for item in normalized), normalized, [], provenance or {})


def canonical_from_whisper(video_id: str, payload: dict[str, Any], *, provenance: dict[str, Any] | None = None) -> CanonicalTranscript:
    words: list[TranscriptWord] = []
    for raw in payload.get("words") or []:
        text = str(raw.get("text") or "")
        if not text.strip() or raw.get("type") == "spacing":
            continue
        words.append(TranscriptWord(text=text.strip(), start=max(0.0, float(raw.get("start", 0))),
                                    end=max(0.0, float(raw.get("end", raw.get("start", 0)))),
                                    type=str(raw.get("type") or "word"), speaker_id=raw.get("speaker_id")))
    segments: list[TranscriptSegment] = []
    for index, raw in enumerate(payload.get("segments") or [], 1):
        text = _clean_text(str(raw.get("text") or ""))
        if text:
            segments.append(TranscriptSegment(f"SEG_{index:04d}", float(raw.get("start", 0)),
                                               float(raw.get("end", raw.get("start", 0))), text))
    if not segments:
        segments = _segments_from_words(words)
    language = str(payload.get("language_code") or payload.get("language") or "unknown")
    return CanonicalTranscript("1.0", video_id, language, "ASR_WHISPER", "faster-whisper", _now(),
                               " ".join(item.text for item in segments), segments, words, provenance or {})


def write_canonical(path: Path, transcript: CanonicalTranscript) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(transcript.to_dict(), ensure_ascii=False, indent=2) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def write_transcript_markdown(path: Path, transcript: CanonicalTranscript) -> None:
    lines = [f"# Transcript: {transcript.video_id}", "", f"- Source: `{transcript.source_type}`",
             f"- Provider: `{transcript.provider}`", f"- Language: `{transcript.language}`", "", "## Segments", ""]
    for segment in transcript.segments:
        lines.append(f"- `{format_timestamp(segment.start)}–{format_timestamp(segment.end)}` {segment.text}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def format_timestamp(value: float) -> str:
    total = max(0, int(value))
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"
