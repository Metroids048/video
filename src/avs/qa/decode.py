"""Full media decode validation."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def decode_error(path: Path) -> str | None:
    if not shutil.which("ffmpeg"):
        return "ffmpeg 不可用"
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
        capture_output=True, text=True, timeout=180,
    )
    return None if result.returncode == 0 else (result.stderr or "完整解码失败")[-500:]
