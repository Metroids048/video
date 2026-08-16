"""Prepare the data-driven 22.5s Pilot from the locked final narration."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from avs.render.captions import build_srt_from_words


def tokenize(text: str) -> list[str]:
    """Keep product names and numeric evidence as atomic caption tokens."""
    pattern = r"Claude Code|Binance Demo|Why No Trade|5000U|7350U|Codex|[A-Za-z]+|[0-9]+(?:[×xX][0-9]+)?|[\u4e00-\u9fff]"
    return re.findall(pattern, text.replace("\n", ""))


def run(args: list[str]) -> None:
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("episode", type=Path)
    args = parser.parse_args()
    ep = args.episode.resolve()
    audio = ep / "work" / "audio" / "narration-final-48k.wav"
    words_path = ep / "work" / "final-narration.words.json"
    if not audio.is_file() or not words_path.is_file():
        raise SystemExit("closeout audio artifacts are missing")

    plan = {
        "version": "2.0",
        "source": "Creative Contract + Evidence Map + locked narration",
        "variants": {
            "primary": [
                {"start": 0.0, "duration": 4.5, "in": 1.0, "region": [0.02, 0.05, 0.72, 0.90], "target": "Dashboard overview", "spoken": "我这几个月一直在用 AI 做一套自动交易系统。"},
                {"start": 4.5, "duration": 4.5, "in": 129.0, "region": [0.05, 0.42, 0.92, 0.50], "target": "Binance Demo order history", "spoken": "交易所模拟盘从 5000U 到约 7350U，只是阶段快照。"},
                {"start": 9.0, "duration": 4.5, "in": 84.0, "region": [0.42, 0.24, 0.58, 0.60], "target": "Why No Trade", "spoken": "为什么这次没开单？Why No Trade 会留下原因。"},
                {"start": 13.5, "duration": 4.5, "in": 145.0, "region": [0.0, 0.0, 1.0, 0.65], "target": "Decision and risk", "spoken": "行情先判断，再过风控；Codex 和 Claude Code 负责实现。"},
                {"start": 18.0, "duration": 4.5, "in": 136.0, "region": [0.0, 0.42, 1.0, 0.44], "target": "Binance Demo balance", "spoken": "最后回到 Binance Demo 对账，才算真的跑通。"},
            ]
        }
    }
    plan_path = ep / "work" / "content" / "pilot-shot-plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    pilot_dir = ep / "work" / "pilots" / "primary"
    pilot_dir.mkdir(parents=True, exist_ok=True)
    segments: list[Path] = []
    for index, spec in enumerate(plan["variants"]["primary"]):
        segment = pilot_dir / f"audio-{index:02}.wav"
        run(["ffmpeg", "-y", "-ss", str(spec["start"]), "-i", str(audio), "-t", str(spec["duration"]), "-ar", "48000", "-ac", "1", str(segment)])
        segments.append(segment)
    concat = pilot_dir / "audio-concat.txt"
    concat.write_text("".join(f"file '{item.resolve().as_posix()}'\n" for item in segments), encoding="utf-8")
    narration = pilot_dir / "narration.mp3"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:a", "libmp3lame", "-b:a", "192k", str(narration)])

    pilot_words: list[dict[str, object]] = []
    for spec in plan["variants"]["primary"]:
        start, end, target = float(spec["start"]), float(spec["start"] + spec["duration"]), str(spec["spoken"])
        tokens = tokenize(target)
        step = (end - start) / max(len(tokens), 1)
        for index, token in enumerate(tokens):
            pilot_words.append({"type": "word", "text": token, "start": round(start + index * step, 3), "end": round(start + (index + 1) * step, 3), "alignment": "canonical_text_constrained"})
    (pilot_dir / "narration.words.json").write_text(json.dumps({"version": "2.0", "audio": str(narration.relative_to(ep)).replace("\\", "/"), "duration": 22.5, "words": pilot_words}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (pilot_dir / "narration.json").write_text(json.dumps({"provider": "GPT-SoVITS-local", "voice_profile": "knowledge/voice/voice-profile.json", "script_source": "work/content/pilot-shot-plan.json", "protected_terms": ["Codex", "Claude Code", "Binance Demo", "Why No Trade", "5000U", "7350U"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    build_srt_from_words(pilot_dir / "narration.words.json", pilot_dir / "captions.srt", total_duration=22.5)
    print(json.dumps({"pilot_audio": str(narration), "words": len(pilot_words), "duration": 22.5}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
