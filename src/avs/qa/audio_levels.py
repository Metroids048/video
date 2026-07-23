"""Audio peak analysis."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

_MAX_VOLUME = re.compile(r"max_volume:\s*(?P<value>-?(?:inf|[0-9.]+))\s*dB", re.IGNORECASE)


def parse_max_volume(output: str) -> float | None:
    match = _MAX_VOLUME.search(output)
    if not match or match.group("value").lower() == "-inf":
        return None
    return float(match.group("value"))


def detect_max_volume(path: Path) -> float | None:
    result = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, timeout=180,
    )
    return parse_max_volume(result.stderr or "")
