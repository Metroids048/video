"""FFmpeg black-frame interval detection."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

_BLACK = re.compile(r"black_start:(?P<start>[0-9.]+)\s+black_end:(?P<end>[0-9.]+)\s+black_duration:(?P<duration>[0-9.]+)")


def parse_black_intervals(output: str) -> list[dict[str, float]]:
    return [{key: float(value) for key, value in match.groupdict().items()} for match in _BLACK.finditer(output)]


def detect_black_intervals(path: Path) -> list[dict[str, float]]:
    result = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path), "-vf", "blackdetect=d=0.5:pix_th=0.02:pic_th=0.999", "-an", "-f", "null", "-"],
        capture_output=True, text=True, timeout=180,
    )
    return parse_black_intervals(result.stderr or "")
