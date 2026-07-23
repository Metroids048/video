"""SRT timing and readability checks."""
from __future__ import annotations

from pathlib import Path

from avs.render.captions import has_subtitle_overflow


def inspect_subtitles(path: Path, total_duration: float) -> dict:
    if not path.is_file():
        return {"missing": True, "overflow": [], "long_lines": []}
    text = path.read_text(encoding="utf-8-sig")
    lines = [line.strip() for line in text.splitlines() if line.strip() and "-->" not in line and not line.strip().isdigit()]
    return {
        "missing": False,
        "overflow": has_subtitle_overflow(path, total_duration),
        "long_lines": [line for line in lines if len(line) > 28],
    }
