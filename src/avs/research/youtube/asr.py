"""Adapter around the repository's existing faster-whisper implementation."""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class ASRResult:
    ok: bool
    payload: dict | None = None
    message: str = ""


def _load_whisper_module():
    root = Path(__file__).resolve().parents[4]
    script = root / "scripts" / "free_providers" / "whisper_transcribe.py"
    spec = importlib.util.spec_from_file_location("avs_existing_whisper_transcribe", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载现有 Whisper 脚本: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FasterWhisperProvider:
    name = "faster-whisper"

    def __init__(self, *, transcriber: Callable[..., dict] | None = None,
                 model_size: str = "small", language: str | None = "zh", device: str = "auto"):
        self.transcriber = transcriber
        self.model_size = model_size
        self.language = language
        self.device = device

    def transcribe(self, media_path: Path, *, video_id: str, provenance: dict | None = None) -> ASRResult:
        try:
            fn = self.transcriber or _load_whisper_module().transcribe_to_scribe_json
            payload = fn(media_path, model_size=self.model_size, language=self.language, device=self.device)
            if not isinstance(payload, dict):
                return ASRResult(False, message="Whisper provider returned non-object payload")
            payload = dict(payload)
            payload.setdefault("video_id", video_id)
            if provenance:
                payload["provenance"] = provenance
            return ASRResult(True, payload=payload)
        except Exception as exc:  # noqa: BLE001 - provider boundary records the failure
            return ASRResult(False, message=str(exc)[:500])
