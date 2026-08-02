"""scripts/free_providers/whisper_transcribe.py — 免费本地转写（faster-whisper）。

输出格式兼容 video-use / ElevenLabs Scribe 的 words[]，可被 pack_transcripts.py 消费。

用法：
  python scripts/free_providers/whisper_transcribe.py <video> --edit-dir <edit>
  python scripts/free_providers/whisper_transcribe.py <video> --language zh --model small
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def extract_audio(video_path: Path, dest: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def words_from_segments(segments) -> list[dict]:
    """Build Scribe-compatible words list with synthetic spacing gaps."""
    words: list[dict] = []
    prev_end: float | None = None
    for seg in segments:
        for w in seg.words or []:
            start = float(w.start)
            end = float(w.end)
            text = (w.word or "").strip()
            if not text:
                continue
            if prev_end is not None and start - prev_end > 0.05:
                words.append(
                    {
                        "type": "spacing",
                        "text": " ",
                        "start": prev_end,
                        "end": start,
                    }
                )
            words.append(
                {
                    "type": "word",
                    "text": text,
                    "start": start,
                    "end": end,
                    "speaker_id": "speaker_0",
                }
            )
            prev_end = end
    return words


def transcribe_to_scribe_json(
    video: Path,
    *,
    model_size: str = "small",
    language: str | None = None,
    device: str = "auto",
) -> dict:
    from faster_whisper import WhisperModel

    compute = "int8"
    if device == "auto":
        try:
            import torch  # type: ignore

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:  # noqa: BLE001
            device = "cpu"

    model = WhisperModel(model_size, device=device, compute_type=compute)
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{video.stem}.wav"
        extract_audio(video, audio)
        segments, info = model.transcribe(
            str(audio),
            language=language,
            word_timestamps=True,
            vad_filter=True,
        )
        seg_list = list(segments)

    words = words_from_segments(seg_list)
    text = " ".join(w["text"] for w in words if w.get("type") == "word")
    return {
        "provider": "faster-whisper",
        "model": model_size,
        "language_code": getattr(info, "language", language) or "unknown",
        "text": text,
        "words": words,
        "free_tier": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Free local Whisper transcription (Scribe-compatible JSON)")
    ap.add_argument("video", type=Path)
    ap.add_argument("--edit-dir", type=Path, default=None)
    ap.add_argument("--language", type=str, default=None)
    ap.add_argument("--model", type=str, default="small", help="tiny|base|small|medium|large-v3")
    ap.add_argument("--device", type=str, default="auto")
    args = ap.parse_args()

    video = args.video.resolve()
    if not video.is_file():
        print(f"video not found: {video}", file=sys.stderr)
        return 1

    edit_dir = (args.edit_dir or (video.parent / "edit")).resolve()
    out_dir = edit_dir / "transcripts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{video.stem}.json"
    if out_path.exists():
        print(f"cached: {out_path}")
        return 0

    t0 = time.time()
    payload = transcribe_to_scribe_json(
        video,
        model_size=args.model,
        language=args.language,
        device=args.device,
    )
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"saved: {out_path} words={len(payload['words'])} in {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
