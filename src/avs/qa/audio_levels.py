"""Audio level analysis and publishability gates."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

_MAX_VOLUME = re.compile(r"max_volume:\s*(?P<value>-?(?:inf|[0-9.]+))\s*dB", re.IGNORECASE)
_MEAN_VOLUME = re.compile(r"mean_volume:\s*(?P<value>-?(?:inf|[0-9.]+))\s*dB", re.IGNORECASE)


def _parse_level(output: str, pattern: re.Pattern[str]) -> float | None:
    match = pattern.search(output)
    if not match or match.group("value").lower() == "-inf":
        return None
    return float(match.group("value"))


def parse_max_volume(output: str) -> float | None:
    return _parse_level(output, _MAX_VOLUME)


def parse_mean_volume(output: str) -> float | None:
    return _parse_level(output, _MEAN_VOLUME)


def detect_audio_levels(path: Path) -> tuple[float | None, float | None]:
    result = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    output = result.stderr or ""
    return parse_mean_volume(output), parse_max_volume(output)


def detect_max_volume(path: Path) -> float | None:
    _mean_db, max_db = detect_audio_levels(path)
    return max_db


def audio_is_publishable(*, has_audio: bool, mean_db: float | None, max_db: float | None) -> bool:
    """Return True only for an actually audible track, not just a present stream.

    The bounds are intentionally broad. This is a hard failure gate for absent or
    practically silent media, not a mastering-quality score.
    """
    if not has_audio or mean_db is None or max_db is None:
        return False
    return mean_db >= -45.0 and max_db >= -20.0
