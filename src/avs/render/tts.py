"""Free Edge TTS narration for Active Episodes."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _spoken_text(script: dict[str, Any]) -> str:
    lines = [
        str(segment.get("spoken_text") or segment.get("text") or "").strip()
        for segment in script.get("segments", [])
    ]
    return "\n".join(line for line in lines if line)


def ensure_edge_narration(
    episode_dir: Path,
    script: dict[str, Any],
    *,
    force: bool = False,
    voice: str = "zh-CN-YunxiNeural",
    rate: str = "+8%",
) -> Path:
    """Generate a free working narration without modifying Episode inputs."""
    output = episode_dir / "work" / "prepared" / "generated" / "narration.mp3"
    if output.is_file() and output.stat().st_size > 0 and not force:
        return output
    text = _spoken_text(script)
    if not text:
        raise RuntimeError("脚本没有可用于配音的 spoken_text")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, "-m", "edge_tts",
        "--voice", voice,
        "--rate", rate,
        "--text", text,
        "--write-media", str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180, check=False)
    if result.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        output.unlink(missing_ok=True)
        detail = (result.stderr or result.stdout or "未知错误")[-500:]
        raise RuntimeError(f"Edge TTS 旁白生成失败 (exit {result.returncode}): {detail}")
    provenance = {
        "provider": "edge_tts",
        "voice": voice,
        "rate": rate,
        "script_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "output": output.relative_to(episode_dir).as_posix(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    provenance_path = episode_dir / "work" / "generated" / "narration.json"
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
