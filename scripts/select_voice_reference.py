"""Extract and score candidate speaker references from the original recording."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EP = ROOT / "episodes" / "active" / "EP-20260812-01-V2"
SOURCE = EP / "work" / "audio" / "source-voice-full.wav"
OUT = EP / "work" / "audio" / "voice-references"
CANDIDATES = [("A", 33.16, 48.42), ("B", 52.58, 65.88), ("C", 68.60, 83.24)]


def run(args: list[str], capture: bool = False) -> str:
    result = subprocess.run(args, check=True, text=True, capture_output=capture)
    return (result.stdout or "") + (result.stderr or "")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for label, start, end in CANDIDATES:
        clean = OUT / f"voice-ref-{label}-clean.wav"
        run(["ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", str(SOURCE), "-af", "highpass=f=80,lowpass=f=12000,adeclick,loudnorm=I=-18:TP=-2:LRA=7", "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(clean)])
        report = run(["ffmpeg", "-i", str(clean), "-af", "silencedetect=n=-42dB:d=0.25,astats=metadata=1:reset=1", "-f", "null", "-"], capture=True)
        silent = report.count("silence_start")
        duration = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(clean)], text=True).strip())
        results.append({"label": label, "source_start": start, "source_end": end, "duration": duration, "silence_events_ge_0_25s": silent, "path": str(clean), "sha256": sha256(clean)})
    results.sort(key=lambda item: (item["silence_events_ge_0_25s"], -item["duration"]))
    lock = {"source_video": str(EP / "work" / "prepared" / "screen" / "20260812_131106.mp4"), "selected": results[0], "candidates": results}
    (EP / "work" / "audio" / "VOICE_REFERENCE_LOCK.json").write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(lock, ensure_ascii=False))


if __name__ == "__main__":
    main()
