#!/usr/bin/env python3
"""Heuristic linter for LTX-2.3 prompts and Prompt Relay text.

This script checks common structural risks. It does not call a model and cannot
predict generation quality. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


@dataclass
class Finding:
    level: str
    code: str
    message: str


CAMERA_TERMS = {
    "static": ["static camera", "locked camera", "locked-off", "tripod"],
    "handheld": ["handheld"],
    "orbit": ["orbit", "circle around"],
    "push": ["push-in", "push in", "dolly in"],
    "pull": ["pull-back", "pull back", "dolly out"],
    "pan": ["pan left", "pan right", "pans left", "pans right"],
    "track": ["tracking shot", "tracks left", "tracks right", "lateral track"],
    "jib": ["jib", "crane up", "crane down"],
    "cuts": ["rapid cuts", "hard cuts", "montage"],
    "continuous": ["continuous take", "single take", "one take"],
}

ACTION_CONNECTORS = [
    "at first", "then", "next", "finally", "a beat later", "as ", "while ",
    "after ", "before ", "begins", "starts", "ends", "settles"
]

DIALOGUE_RE = re.compile(r'["“”](.+?)["“”]')
BLOCK_HEADER_RE = re.compile(r"(?mi)^\s*[A-Za-z_\- ]+\s+\d+(?:\s*[-–]\s*\d+)?\s*:\s*$")
WEIGHT_RE = re.compile(r"\[(\d+(?:\.\d+)?)(?:\s*[-–]\s*(\d+(?:\.\d+)?))?\]")


def contains_any(text: str, phrases: Iterable[str]) -> bool:
    t = text.lower()
    return any(p in t for p in phrases)


def split_relay(text: str) -> tuple[str, list[str]]:
    has_pipe = "|" in text
    headers = list(BLOCK_HEADER_RE.finditer(text))
    if has_pipe and headers:
        return "mixed", []
    if has_pipe:
        return "inline", [s.strip() for s in text.split("|") if s.strip()]
    if headers:
        segments = []
        for i, match in enumerate(headers):
            start = match.end()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
            body = text[start:end].strip()
            if body:
                segments.append(body)
        return "block", segments
    return "none", [text.strip()] if text.strip() else []


def lint(text: str, mode: str, duration: float | None) -> list[Finding]:
    findings: list[Finding] = []
    lower = text.lower()
    words = re.findall(r"\b[\w'-]+\b", text)
    word_count = len(words)

    if not text.strip():
        return [Finding("error", "EMPTY", "Prompt is empty.")]

    if word_count < 12 and mode not in {"i2v", "v2v"}:
        findings.append(Finding("warning", "VERY_SHORT", "The prompt may be too sparse for subject, action, camera and audio control."))

    if duration:
        density = word_count / duration
        if density > 28:
            findings.append(Finding("warning", "HIGH_DENSITY", f"Prompt density is {density:.1f} words/second; consider removing decoration or segmenting actions."))
        if duration <= 5 and len(DIALOGUE_RE.findall(text)) > 1:
            findings.append(Finding("warning", "DIALOGUE_OVERLOAD", "Multiple dialogue lines in a very short clip are likely to be truncated or assigned incorrectly."))

    active_camera = [name for name, terms in CAMERA_TERMS.items() if contains_any(text, terms)]
    if "static" in active_camera and any(x in active_camera for x in ("handheld", "orbit", "push", "pull", "pan", "track", "jib")):
        findings.append(Finding("error", "CAMERA_CONFLICT", "Static/locked camera conflicts with an active camera movement."))
    if "cuts" in active_camera and "continuous" in active_camera:
        findings.append(Finding("error", "EDITING_CONFLICT", "Rapid cuts/montage conflicts with a continuous single take."))
    movement_count = len([x for x in active_camera if x not in {"static", "cuts", "continuous"}])
    if movement_count >= 3:
        findings.append(Finding("warning", "CAMERA_OVERLOAD", f"Detected {movement_count} camera movement families; use one primary move and one compatible secondary move."))

    if "preserve" in lower and any(p in lower for p in ["change everything", "entirely different", "completely replace the scene"]):
        findings.append(Finding("error", "PRESERVE_CONFLICT", "Preservation language conflicts with a global replacement instruction."))

    if any(p in lower for p in ["supplied audio", "reference audio", "exact timing guide"]) and DIALOGUE_RE.search(text):
        findings.append(Finding("warning", "AUDIO_SCRIPT_CONFLICT", "The prompt contains quoted dialogue while also treating supplied audio as exact; verify that the text matches the track and is required by the workflow."))

    if mode == "i2v":
        static_markers = ["wearing", "background", "hair", "eyes", "face", "dress", "shirt", "room", "located"]
        motion_markers = ["moves", "turns", "walks", "runs", "blinks", "breath", "opens", "closes", "leans", "raises", "lowers", "camera"]
        static_hits = sum(lower.count(x) for x in static_markers)
        motion_hits = sum(lower.count(x) for x in motion_markers)
        if static_hits > motion_hits + 3:
            findings.append(Finding("warning", "I2V_STATIC_REDUNDANCY", "The I2V prompt appears to redescribe static appearance more than motion; focus on what changes after the first frame."))

    relay_style, segments = split_relay(text)
    if mode == "relay" or relay_style != "none":
        if relay_style == "mixed":
            findings.append(Finding("error", "RELAY_MIXED_SYNTAX", "Do not mix pipe-separated and block-header Prompt Relay syntax."))
            return findings
        if len(segments) < 2:
            findings.append(Finding("error", "RELAY_SEGMENTS", "Prompt Relay needs at least two non-empty segments."))
        if segments:
            first = segments[0].lower()
            first_motion = sum(first.count(x) for x in ["walks", "runs", "turns", "opens", "speaks", "says", "jumps", "moves"])
            if first_motion >= 2:
                findings.append(Finding("warning", "RELAY_ANCHOR_MOTION", "The first segment should usually be a static global anchor, not a multi-action beat."))
            for idx, seg in enumerate(segments[1:], 2):
                if len(re.findall(r"\b\w+\b", seg)) > 95:
                    findings.append(Finding("warning", "RELAY_LONG_SEGMENT", f"Segment {idx} is long; keep one dominant change/speaker/camera implication per beat."))
        weights = WEIGHT_RE.findall(text)
        for a, b in weights:
            if b and float(b) <= float(a):
                findings.append(Finding("error", "RELAY_BAD_RANGE", f"Invalid non-increasing relative range [{a}-{b}]."))

    quote_chars = sum(text.count(c) for c in ['"', '“', '”'])
    if quote_chars % 2:
        findings.append(Finding("error", "UNBALANCED_QUOTES", "Dialogue quotation marks appear unbalanced."))

    lines = DIALOGUE_RE.findall(text)
    if lines:
        long_lines = [line for line in lines if len(re.findall(r"\S+", line)) > 24 or len(line) > 90]
        if long_lines:
            findings.append(Finding("warning", "LONG_DIALOGUE", "At least one quoted line is long; shorten it or allocate more time/custom audio."))
        if not any(label in lower for label in ["camera left", "camera right", "on the left", "on the right", "speaker", "woman", "man", "character"]):
            findings.append(Finding("warning", "SPEAKER_AMBIGUITY", "Dialogue is present but speaker identity/location may be ambiguous."))

    if not any(connector in lower for connector in ACTION_CONNECTORS) and word_count > 80:
        findings.append(Finding("warning", "WEAK_TEMPORAL_ORDER", "Long prompt has few chronological connectors; clarify event order."))

    if any(x in lower for x in ["perfect readable text", "exact logo", "flawless typography"]):
        findings.append(Finding("warning", "TYPOGRAPHY_EXPECTATION", "Exact text/logo fidelity is better handled in post-production."))

    if not findings:
        findings.append(Finding("info", "CLEAN", "No common structural risks detected. This does not guarantee generation quality."))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint an LTX-2.3 prompt or Prompt Relay script.")
    parser.add_argument("input", type=Path, help="UTF-8 text file containing the prompt")
    parser.add_argument("--mode", choices=["t2v", "i2v", "a2v", "v2v", "relay", "dialogue", "auto"], default="auto")
    parser.add_argument("--duration", type=float, default=None, help="Target duration in seconds")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    try:
        text = args.input.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot read {args.input}: {exc}", file=sys.stderr)
        return 2

    mode = args.mode
    if mode == "auto":
        style, segs = split_relay(text)
        mode = "relay" if style != "none" else "t2v"

    findings = lint(text, mode, args.duration)
    if args.json:
        payload = {
            "file": str(args.input),
            "mode": mode,
            "duration": args.duration,
            "findings": [asdict(x) for x in findings],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for item in findings:
            print(f"[{item.level.upper()}] {item.code}: {item.message}")

    return 1 if any(x.level == "error" for x in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
