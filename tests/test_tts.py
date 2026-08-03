"""Free narration generation contracts."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from avs.render.tts import ensure_edge_narration


def test_edge_tts_generates_working_audio_and_provenance(tmp_path: Path) -> None:
    ep_dir = tmp_path / "episodes" / "active" / "EP-TTS"
    script = {
        "segments": [
            {"spoken_text": "第一段。"},
            {"spoken_text": "第二段。"},
        ],
    }

    def fake_run(command, **_kwargs):
        output = Path(command[command.index("--write-media") + 1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"ID3-audio")
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    with patch("avs.render.tts.subprocess.run", side_effect=fake_run) as run:
        output = ensure_edge_narration(ep_dir, script, force=True)

    assert output == ep_dir / "work" / "prepared" / "generated" / "narration.mp3"
    command = run.call_args.args[0]
    assert "edge_tts" in command
    assert command[command.index("--voice") + 1] == "zh-CN-YunxiNeural"
    provenance = json.loads(
        (ep_dir / "work" / "generated" / "narration.json").read_text(encoding="utf-8")
    )
    assert provenance["provider"] == "edge_tts"
    assert provenance["script_sha256"]


def test_edge_tts_is_idempotent_without_force(tmp_path: Path) -> None:
    ep_dir = tmp_path / "EP-TTS"
    output = ep_dir / "work" / "prepared" / "generated" / "narration.mp3"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"existing")

    with patch("avs.render.tts.subprocess.run") as run:
        assert ensure_edge_narration(ep_dir, {"segments": []}) == output

    run.assert_not_called()
