"""Free narration generation contracts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

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
    """复用需要 provenance 证明音频出自当前脚本，而不只是文件存在。"""
    ep_dir = tmp_path / "EP-TTS"
    script = {"segments": [{"spoken_text": "一句口播。"}]}
    output = ep_dir / "work" / "prepared" / "generated" / "narration.mp3"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"existing")
    provenance = ep_dir / "work" / "generated" / "narration.json"
    provenance.parent.mkdir(parents=True)
    provenance.write_text(json.dumps({
        "script_sha256": hashlib.sha256("一句口播。".encode("utf-8")).hexdigest(),
        "voice": "zh-CN-YunxiNeural",
        "rate": "+8%",
    }), encoding="utf-8")

    with patch("avs.render.tts.subprocess.run") as run:
        assert ensure_edge_narration(ep_dir, script) == output

    run.assert_not_called()


def test_edge_tts_regenerates_when_provenance_is_absent(tmp_path: Path) -> None:
    """无 provenance 的旧音频不可复用：无法证明它对应当前脚本。"""
    ep_dir = tmp_path / "EP-TTS"
    output = ep_dir / "work" / "prepared" / "generated" / "narration.mp3"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"stale-from-previous-script")

    def fake_run(command, **_kwargs):
        Path(command[command.index("--write-media") + 1]).write_bytes(b"fresh")
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    with patch("avs.render.tts.subprocess.run", side_effect=fake_run) as run:
        ensure_edge_narration(ep_dir, {"segments": [{"spoken_text": "新脚本。"}]})

    run.assert_called_once()
    assert output.read_bytes() == b"fresh"


def test_edge_tts_rejects_empty_script_even_with_existing_audio(tmp_path: Path) -> None:
    """空脚本必须一致地失败，而不是靠已存在的旧音频蒙混过关。"""
    ep_dir = tmp_path / "EP-TTS"
    output = ep_dir / "work" / "prepared" / "generated" / "narration.mp3"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"existing")

    with pytest.raises(RuntimeError, match="spoken_text"):
        ensure_edge_narration(ep_dir, {"segments": []})
