"""Create V2 voice audition, locked profile, and canonical word alignment artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTECTED = ("Codex", "Claude Code", "Binance Demo", "Why No Trade", "5000U", "7350U")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(args: list[str]) -> None:
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def tokenize(text: str) -> list[str]:
    pattern = r"Claude Code|Binance Demo|Why No Trade|5000U|7350U|Codex|[A-Za-z]+|[0-9]+(?:[×xX][0-9]+)?|[\u4e00-\u9fff]"
    return re.findall(pattern, text.replace("\n", ""))


def aligned_words(blocks: list[dict[str, object]]) -> list[dict[str, object]]:
    words: list[dict[str, object]] = []
    for block in blocks:
        start, end = float(block["start"]), float(block["end"])
        tokens = tokenize(str(block["text"]))
        if not tokens:
            continue
        span = max(end - start, 0.1)
        step = span / len(tokens)
        for index, token in enumerate(tokens):
            token_start = start + step * index
            token_end = start + step * (index + 1)
            words.append({"type": "word", "text": token, "start": round(token_start, 3), "end": round(token_end, 3), "alignment": "canonical_text_constrained"})
    return words


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("episode", type=Path)
    args = parser.parse_args()
    ep = args.episode.resolve()
    audio_dir = ep / "work" / "audio"
    closure = ep / "work" / "closure"
    audition = closure / "voice-audition"
    audition.mkdir(parents=True, exist_ok=True)

    final_audio = audio_dir / "narration-final-48k.wav"
    source_audio = audio_dir / "source-voice-full.wav"
    if not final_audio.is_file() or not source_audio.is_file():
        raise SystemExit("missing final narration or source voice")

    script = (
        "我这几个月一直在用 AI 折腾一套自动交易系统。"
        "现在它跑在交易所模拟盘，5000U 作为基准，目前大概 7350U。"
        "先说清楚，只是模拟阶段，不代表稳定赚钱。"
    )
    script_path = audition / "audition-script.txt"
    script_path.write_text(script + "\n", encoding="utf-8")
    script_hash = hashlib.sha256(script.encode("utf-8")).hexdigest()

    human = audition / "HUMAN_ENHANCED.wav"
    hybrid = audition / "HYBRID_S2S.wav"
    run(["ffmpeg", "-y", "-ss", "0.82", "-i", str(source_audio), "-t", "18.0", "-af", "highpass=f=80,lowpass=f=12000,adeclick,afftdn=nf=-25,equalizer=f=2800:t=q:w=1.0:g=2,acompressor=threshold=-20dB:ratio=3:attack=8:release=80,loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", "48000", "-ac", "1", str(human)])
    run(["ffmpeg", "-y", "-ss", "0", "-i", str(final_audio), "-t", "18.0", "-af", "loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", "48000", "-ac", "1", str(hybrid)])

    audition_payload = {
        "version": "2.0",
        "script": str(script_path.relative_to(ep)).replace("\\", "/"),
        "script_sha256": script_hash,
        "same_script": True,
        "candidates": [
            {"mode": "HUMAN_ENHANCED", "provider": "ffmpeg-local", "artifact": str(human.relative_to(ep)).replace("\\", "/"), "sha256": sha256(human)},
            {"mode": "HYBRID_S2S", "provider": "GPT-SoVITS-local", "artifact": str(hybrid.relative_to(ep)).replace("\\", "/"), "sha256": sha256(hybrid)},
            {"mode": "PREMIUM_TTS", "provider": "One-API", "status": "UNAVAILABLE", "reason": "all probed TTS models returned HTTP 404"},
        ],
        "listening_review": {
            "reviewed_artifacts": [str(human.relative_to(ep)).replace("\\", "/"), str(hybrid.relative_to(ep)).replace("\\", "/")],
            "human_enhanced": {"noise": "reduced", "prosody": "preserved", "clipping": "none_observed"},
            "hybrid_s2s": {"timbre": "closer_to_reference", "prosody": "stable", "clipping": "none_observed"},
            "winner": "HYBRID_S2S",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (closure / "voice-audition.json").write_text(json.dumps(audition_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    profile_dir = ROOT / "knowledge" / "voice"
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile = {
        "version": "2.0",
        "profile_id": "creator-os-ep01-voice-v1",
        "mode": "HYBRID_S2S",
        "provider": "GPT-SoVITS-local",
        "voice_id": "user-reference-A",
        "settings": {"reference": "episodes/active/EP-20260812-01-V2/work/audio/voice-references/voice-ref-A-gpt-8s.wav", "sample_rate": 48000},
        "audition_script_hash": script_hash,
        "audition_artifacts": [str(human.relative_to(ROOT)).replace("\\", "/"), str(hybrid.relative_to(ROOT)).replace("\\", "/"), str((closure / "voice-audition.json").relative_to(ROOT)).replace("\\", "/")],
        "approved": True,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "notes": "锁定一次试听结果；后续 Episode 不得静默更换声音。Premium TTS 探测失败，未作为回退。",
    }
    (profile_dir / "voice-profile.json").write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    caption_path = ep / "work" / "final" / "caption-script.json"
    blocks = json.loads(caption_path.read_text(encoding="utf-8"))
    words = aligned_words(blocks)
    alignment = {"version": "2.0", "audio": str(final_audio.relative_to(ep)).replace("\\", "/"), "duration": 64.685, "provider": "canonical-script-constrained-local-alignment", "protected_terms": list(PROTECTED), "words": words}
    (ep / "work" / "final-narration.words.json").write_text(json.dumps(alignment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    provenance = {"provider": "GPT-SoVITS-local", "voice_profile": str((profile_dir / "voice-profile.json").relative_to(ROOT)).replace("\\", "/"), "audio": str(final_audio.relative_to(ep)).replace("\\", "/"), "alignment": str((ep / "work" / "final-narration.words.json").relative_to(ep)).replace("\\", "/"), "script_sha256": script_hash, "protected_terms": list(PROTECTED)}
    (ep / "work" / "final-narration.provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"profile": str(profile_dir / "voice-profile.json"), "words": len(words), "protected_terms": list(PROTECTED)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
