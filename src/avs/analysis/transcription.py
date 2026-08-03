"""Local Whisper timestamp extraction for Manifest voice assets."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def transcribe_audio_assets(episode_dir: Path, manifest: dict[str, Any], *, model: str = "base") -> dict[str, Any]:
    voice_assets = [
        asset for asset in manifest.get("assets", [])
        if asset.get("source_type") == "audio"
        and asset.get("audio_role") in {"narration", "original_voice"}
        and asset.get("status") == "ok"
    ]
    executable = shutil.which("whisper")
    transcripts: list[dict[str, Any]] = []
    blocked = bool(voice_assets and executable is None)
    reason = "本地 whisper CLI 不可用，真实语音未转写" if blocked else None
    if executable:
        for asset in voice_assets:
            source = episode_dir / str(asset.get("working_path"))
            with tempfile.TemporaryDirectory(prefix="avs_whisper_") as temporary:
                result = subprocess.run(
                    [executable, str(source), "--model", model, "--output_format", "json", "--output_dir", temporary],
                    capture_output=True,
                    text=True,
                    timeout=1800,
                    check=False,
                )
                output = Path(temporary) / f"{source.stem}.json"
                if result.returncode != 0 or not output.is_file():
                    blocked = True
                    reason = f"语音 {asset['asset_id']} 转写失败"
                    continue
                value = json.loads(output.read_text(encoding="utf-8"))
                transcripts.append({
                    "asset_id": asset["asset_id"],
                    "text": value.get("text", ""),
                    "segments": value.get("segments", []),
                })
    doc = {"episode_id": manifest["episode_id"], "blocked": blocked, "blocking_reason": reason, "transcripts": transcripts}
    output_path = episode_dir / "work" / "analysis" / "transcription.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc
