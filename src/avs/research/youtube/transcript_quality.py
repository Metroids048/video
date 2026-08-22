"""Deterministic transcript quality gate used before accepting a provider result."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Iterable

from .transcript import CanonicalTranscript


@dataclass
class TranscriptQA:
    status: str
    reasons: list[str] = field(default_factory=list)
    segment_count: int = 0
    word_count: int = 0
    coverage_seconds: float = 0.0
    coverage_ratio: float | None = None
    language_ok: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def _overlap_seconds(segments: Iterable) -> float:
    ordered = sorted((float(s.start), float(s.end)) for s in segments if s.end >= s.start)
    total = 0.0
    last_end = -1.0
    for start, end in ordered:
        if start > last_end:
            total += end - start
            last_end = end
        elif end > last_end:
            total += end - last_end
            last_end = end
    return total


def assess_transcript(transcript: CanonicalTranscript, *, duration: float | None = None) -> TranscriptQA:
    reasons: list[str] = []
    text = transcript.text.strip()
    if not text:
        reasons.append("EMPTY_TEXT")
    if not transcript.segments:
        reasons.append("NO_SEGMENTS")
    starts = [float(item.start) for item in transcript.segments]
    ends = [float(item.end) for item in transcript.segments]
    if any(start < 0 or end < start for start, end in zip(starts, ends)):
        reasons.append("INVALID_TIMESTAMPS")
    if any(left > right for left, right in zip(starts, starts[1:])):
        reasons.append("NON_MONOTONIC_TIMESTAMPS")
    if text and len(text) < 12:
        reasons.append("TEXT_TOO_SHORT")
    normalized = re.sub(r"\s+", "", text)
    if len(normalized) >= 30 and len(set(normalized[i:i + 12] for i in range(0, len(normalized) - 11, 4))) <= 2:
        reasons.append("REPEATING_TEXT")
    coverage = _overlap_seconds(transcript.segments)
    ratio = None if not duration or duration <= 0 else min(1.0, coverage / duration)
    if duration and duration >= 60 and ratio is not None and ratio < 0.01:
        reasons.append("COVERAGE_TOO_LOW")
    if duration and duration >= 120 and ratio is not None and ratio < 0.03:
        reasons.append("EARLY_STOP_OR_SHORT")
    status = "FAIL" if any(reason in reasons for reason in ("EMPTY_TEXT", "NO_SEGMENTS", "INVALID_TIMESTAMPS",
                                                              "NON_MONOTONIC_TIMESTAMPS", "REPEATING_TEXT", "COVERAGE_TOO_LOW",
                                                              "EARLY_STOP_OR_SHORT")) else ("WARN" if reasons else "PASS")
    return TranscriptQA(status=status, reasons=reasons, segment_count=len(transcript.segments),
                        word_count=len([word for word in transcript.words if word.type == "word"]),
                        coverage_seconds=round(coverage, 3), coverage_ratio=ratio,
                        language_ok=transcript.language != "unknown")
