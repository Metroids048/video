"""Audition the current Jianying TTS account without provider fallback."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = ROOT / "third_party_skills" / "jianying-editor" / "scripts"
OUT = ROOT / "episodes" / "active" / "EP-20260812-01-V2" / "work" / "final" / "audio" / "auditions"
TEXT = "我这几个月一直在拿 AI 折腾一个东西，想把一套自动交易系统真的跑起来。现在它已经接到了交易所模拟盘。"
CANDIDATES = [
    {"voice_id": "zh_male_huoli", "voice_name": "活力男声", "reason": "natural male candidate"},
    {"voice_id": "zh_male_xionger_stream_gpu", "voice_name": "熊二直播男声", "reason": "casual male candidate"},
    {"voice_id": "zh_male_yangguang", "voice_name": "阳光男声", "reason": "young male candidate"},
]


async def main() -> int:
    sys.path.insert(0, str(SKILL_SCRIPTS))
    from universal_tts import generate_voice_with_meta

    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for candidate in CANDIDATES:
        output = OUT / f"{candidate['voice_id']}.ogg"
        path, backend = await generate_voice_with_meta(
            TEXT,
            str(output),
            candidate["voice_id"],
            backend="sami",
            allow_fallback=False,
            sami_retries=1,
        )
        results.append({
            **candidate,
            "provider": "jianying-sami" if path and backend == "sami" else None,
            "backend": backend,
            "audio_path": path,
            "status": "AVAILABLE" if path and backend == "sami" else "UNAVAILABLE",
        })
    (OUT / "audition-results.json").write_text(
        json.dumps({"text": TEXT, "candidates": results}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(results, ensure_ascii=False))
    return 0 if any(item["status"] == "AVAILABLE" for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
