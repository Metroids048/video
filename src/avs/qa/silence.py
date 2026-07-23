"""FFmpeg silence interval detection."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

_START = re.compile(r"silence_start:\s*(?P<value>[0-9.]+)")
_END = re.compile(r"silence_end:\s*(?P<end>[0-9.]+)\s*\|\s*silence_duration:\s*(?P<duration>[0-9.]+)")


def parse_silence_intervals(output: str) -> list[dict[str, float]]:
    starts = [float(match.group("value")) for match in _START.finditer(output)]
    ends = [(float(match.group("end")), float(match.group("duration"))) for match in _END.finditer(output)]
    return [
        {"start": starts[index] if index < len(starts) else end - duration, "end": end, "duration": duration}
        for index, (end, duration) in enumerate(ends)
    ]


def detect_silence_intervals(path: Path) -> list[dict[str, float]]:
    result = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path), "-af", "silencedetect=n=-45dB:d=1.5", "-f", "null", "-"],
        capture_output=True, text=True, timeout=180,
    )
    return parse_silence_intervals(result.stderr or "")
