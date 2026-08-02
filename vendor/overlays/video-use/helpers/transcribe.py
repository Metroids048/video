"""Transcribe a video — ElevenLabs Scribe OR free local faster-whisper.

Default backend selection:
  1. AVS_TRANSCRIBE_BACKEND=whisper|elevenlabs|auto (env)
  2. auto → whisper if no ELEVENLABS_API_KEY, else elevenlabs

Whisper output is Scribe-compatible (words[] with type/start/end) so
pack_transcripts.py / render.py keep working.

Usage:
    python helpers/transcribe.py <video_path>
    python helpers/transcribe.py <video_path> --backend whisper
    python helpers/transcribe.py <video_path> --edit-dir /custom/edit
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

SCRIBE_URL = "https://api.elevenlabs.io/v1/speech-to-text"

# Project free provider (Agent Video Studio)
# helpers/ → video-use/ → third_party_skills/ → repo root
_FREE_WHISPER = (
    Path(__file__).resolve().parents[3] / "scripts" / "free_providers" / "whisper_transcribe.py"
)


def load_api_key() -> str | None:
    for candidate in [Path(__file__).resolve().parent.parent / ".env", Path(".env")]:
        if candidate.exists():
            for line in candidate.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == "ELEVENLABS_API_KEY":
                    val = v.strip().strip('"').strip("'")
                    return val or None
    v = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    return v or None


def resolve_backend(explicit: str | None) -> str:
    raw = (explicit or os.environ.get("AVS_TRANSCRIBE_BACKEND") or "auto").strip().lower()
    if raw in {"whisper", "elevenlabs"}:
        return raw
    # auto
    return "elevenlabs" if load_api_key() else "whisper"


def extract_audio(video_path: Path, dest: Path) -> None:
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def call_scribe(
    audio_path: Path,
    api_key: str,
    language: str | None = None,
    num_speakers: int | None = None,
) -> dict:
    data: dict[str, str] = {
        "model_id": "scribe_v1",
        "diarize": "true",
        "tag_audio_events": "true",
        "timestamps_granularity": "word",
    }
    if language:
        data["language_code"] = language
    if num_speakers:
        data["num_speakers"] = str(num_speakers)

    with open(audio_path, "rb") as f:
        resp = requests.post(
            SCRIBE_URL,
            headers={"xi-api-key": api_key},
            files={"file": (audio_path.name, f, "audio/wav")},
            data=data,
            timeout=1800,
        )

    if resp.status_code != 200:
        raise RuntimeError(f"Scribe returned {resp.status_code}: {resp.text[:500]}")

    return resp.json()


def call_whisper(
    video: Path,
    edit_dir: Path,
    language: str | None = None,
    model: str = "small",
) -> Path:
    if not _FREE_WHISPER.is_file():
        raise RuntimeError(f"free whisper helper missing: {_FREE_WHISPER}")
    cmd = [
        sys.executable,
        str(_FREE_WHISPER),
        str(video),
        "--edit-dir",
        str(edit_dir),
        "--model",
        model,
    ]
    if language:
        cmd.extend(["--language", language])
    subprocess.run(cmd, check=True)
    out = edit_dir / "transcripts" / f"{video.stem}.json"
    if not out.is_file():
        raise RuntimeError(f"whisper did not write {out}")
    return out


def transcribe_one(
    video: Path,
    edit_dir: Path,
    api_key: str | None = None,
    language: str | None = None,
    num_speakers: int | None = None,
    verbose: bool = True,
    backend: str = "auto",
    whisper_model: str = "small",
) -> Path:
    transcripts_dir = edit_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcripts_dir / f"{video.stem}.json"

    if out_path.exists():
        if verbose:
            print(f"cached: {out_path.name}")
        return out_path

    chosen = resolve_backend(backend)
    if verbose:
        print(f"  backend={chosen}", flush=True)

    if chosen == "whisper":
        return call_whisper(video, edit_dir, language=language, model=whisper_model)

    if not api_key:
        api_key = load_api_key()
    if not api_key:
        if verbose:
            print("  no ELEVENLABS_API_KEY — falling back to free whisper", flush=True)
        return call_whisper(video, edit_dir, language=language, model=whisper_model)

    if verbose:
        print(f"  extracting audio from {video.name}", flush=True)

    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{video.stem}.wav"
        extract_audio(video, audio)
        size_mb = audio.stat().st_size / (1024 * 1024)
        if verbose:
            print(f"  uploading {video.stem}.wav ({size_mb:.1f} MB)", flush=True)
        payload = call_scribe(audio, api_key, language, num_speakers)

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    dt = time.time() - t0

    if verbose:
        kb = out_path.stat().st_size / 1024
        print(f"  saved: {out_path.name} ({kb:.1f} KB) in {dt:.1f}s")
        if isinstance(payload, dict) and "words" in payload:
            print(f"    words: {len(payload['words'])}")

    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Transcribe a video (whisper free / ElevenLabs)")
    ap.add_argument("video", type=Path, help="Path to video file")
    ap.add_argument("--edit-dir", type=Path, default=None)
    ap.add_argument("--language", type=str, default=None)
    ap.add_argument("--num-speakers", type=int, default=None)
    ap.add_argument(
        "--backend",
        type=str,
        default="auto",
        choices=["auto", "whisper", "elevenlabs"],
        help="auto: whisper when no ElevenLabs key",
    )
    ap.add_argument("--whisper-model", type=str, default="small")
    args = ap.parse_args()

    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"video not found: {video}")

    edit_dir = (args.edit_dir or (video.parent / "edit")).resolve()
    api_key = load_api_key()

    transcribe_one(
        video=video,
        edit_dir=edit_dir,
        api_key=api_key,
        language=args.language,
        num_speakers=args.num_speakers,
        backend=args.backend,
        whisper_model=args.whisper_model,
    )


if __name__ == "__main__":
    main()
