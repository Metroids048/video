"""EP01 FINAL FINAL LOCK: only audio, captions, and existing-screen timing."""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EP = ROOT / "episodes" / "active" / "EP-20260812-01-V2"
SOURCE = EP / "work" / "prepared" / "screen" / "20260812_131106.mp4"
PREVIOUS = EP / "renders" / "preview-final.mp4"
WORK = EP / "work" / "final-final-lock"
RENDERS = EP / "renders"
SKILL_SCRIPTS = ROOT / "third_party_skills" / "jianying-editor" / "scripts"
VOICE = {
    "provider": "jianying-sami",
    "voice_id": "zh_male_huoli",
    "voice_name": "活力男声",
    "model": "Jianying SAMI TTS",
    "language": "zh-CN",
    "style": "natural, young, conversational male",
    "speed": "provider default; auditioned at natural pace",
    "pitch": "provider default",
    "sample_rate": 48000,
    "selected_reason": "The current account accepted this actual Jianying voice. It is the only non-character male candidate confirmed available; the other available candidate is a character/stream voice.",
}

# This is the user's semantic source, preserved without the retired terminology.
CANONICAL = [
    "我这几个月一直在拿 AI 折腾一个东西：想把一套全天候自动交易系统真的跑起来。",
    "现在它已经接到了交易所模拟盘。最开始按 5000U 作为基准，现在账户大概在 7350U 左右。",
    "先说清楚，这只是模拟阶段的结果，我现在不会拿这个数字说策略已经稳定赚钱。",
    "我本职是做 AI 产品的。这个项目我自己一行代码都没写过。",
    "需求怎么拆、系统应该怎么跑、最后怎么验收是我来定，具体实现基本都是我跟 Codex、Claude Code 一轮一轮做出来的。",
    "它现在已经不只是一个显示买卖信号的 Demo。",
    "行情进来以后，系统会先判断有没有交易机会，再经过风控。条件通过才会下单。后面的持仓、订单、止盈止损，还有交易所状态，都会继续自动跟踪。",
    "我后来还专门做了一块：为什么这次没开单？到底是没有信号、条件没通过，还是被风控拦了，系统都会把原因留下来。",
    "策略这边也不是写完就直接跑。我把策略研究、回测和验证单独做成了一套流程。一个策略回测看起来不错，也不会直接扔进自动交易。",
    "最后我还给自己定了个死规则：本地有订单，不算。",
    "我会直接进交易所模拟盘，看账户、仓位和历史订单。两边最后能对上，我才认为这条自动交易链真的跑通了。",
    "现在它还在继续跑。下一步，我主要在验证止盈止损怎么真正跟着市场状态变化。",
]

# The same meaning, with only pronunciation substitutions. Never use as captions.
TTS = [
    "我这几个月一直在拿 AI 折腾一个东西：想把一套全天候自动交易系统真的跑起来。",
    "现在它已经接到了交易所模拟盘。最开始按五千 U 作为基准，现在账户大概在七千三百五十 U 左右。",
    "先说清楚，这只是模拟阶段的结果，我现在不会拿这个数字说策略已经稳定赚钱。",
    "我本职是做 AI 产品的。这个项目我自己一行代码都没写过。",
    "需求怎么拆、系统应该怎么跑、最后怎么验收是我来定，具体实现基本都是我跟 Codex、Claude Code 一轮一轮做出来的。",
    "它现在已经不只是一个显示买卖信号的 Demo。",
    "行情进来以后，系统会先判断有没有交易机会，再经过风控。条件通过才会下单。后面的持仓、订单、止盈止损，还有交易所状态，都会继续自动跟踪。",
    "我后来还专门做了一块：为什么这次没开单？到底是没有信号、条件没通过，还是被风控拦了，系统都会把原因留下来。",
    "策略这边也不是写完就直接跑。我把策略研究、回测和验证单独做成了一套流程。一个策略回测看起来不错，也不会直接扔进自动交易。",
    "最后我还给自己定了个死规则：本地有订单，不算。",
    "我会直接进交易所模拟盘，看账户、仓位和历史订单。两边最后能对上，我才认为这条自动交易链真的跑通了。",
    "现在它还在继续跑。下一步，我主要在验证止盈止损怎么真正跟着市场状态变化。",
]

CAPTIONS = [
    "用 AI 做一套真正能跑的\n7×24 自动交易系统",
    "交易所模拟盘\n5000U → 约7350U",
    "模拟阶段结果\n不等于稳定收益",
    "这个项目\n我一行代码都没写",
    "Codex + Claude Code\n负责实现",
    "不只是买卖信号 Demo",
    "行情 → 判断 → 风控 → 自动执行\n持仓 / 订单 / 止盈止损 / 状态同步",
    "为什么这次没开单？\n没信号 / 条件没过 / 风控拦截",
    "策略研究 / 回测 / 验证\n回测好，不等于直接自动交易",
    "本地有单 ≠ 真实成交",
    "直接看交易所模拟盘\n账户 / 仓位 / 历史订单",
    "还在继续跑\n下一步：验证止盈止损如何跟随市场",
]

# Existing mature V8 screen areas, ordered exactly to the frozen video structure.
SCENES = [
    ("exchange-hook", 128.0, 140.0, "Loaded Binance Demo Trading account"),
    ("exchange-result", 140.0, 151.8, "Loaded Binance Demo Trading balance and orders"),
    ("maker", 0.0, 24.0, "Project and Codex/Claude Code evidence"),
    ("flow", 66.9, 84.0, "Trading decision, risk, orders and positions"),
    ("why-no-trade", 84.0, 97.0, "Why No Trade system page"),
    ("research", 109.3, 121.3, "Strategy research, backtest and validation"),
    ("exchange-proof", 128.0, 145.0, "Loaded Binance Demo Trading proof"),
    ("next-step", 159.65, 168.0, "Trading workspace next step"),
]
SCENE_PARTS = [[0, 1], [2], [3, 4, 5], [6], [7], [8], [9, 10], [11]]
FORBIDDEN = ("七乘二十四小时", "七乘二十四", "五千 U", "五千U", "七千三百五十 U", "七千三百五十U", "Binance Testnet", "Testnet", "我不会传统编程", "我不是传统程序员", "Why No Trade")
REQUIRED = ("AI", "7×24", "5000U", "7350U", "Codex", "Claude Code")


def run(args: list[str]) -> None:
    subprocess.run(args, check=True)


def probe(path: Path, field: str) -> str:
    return subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", field, "-of", "default=nk=1:nw=1", str(path)], text=True).strip()


def duration(path: Path) -> float:
    return float(probe(path, "format=duration"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ts(value: float) -> str:
    millis = round(value * 1000)
    h, millis = divmod(millis, 3_600_000)
    m, millis = divmod(millis, 60_000)
    s, millis = divmod(millis, 1000)
    return f"{h:02}:{m:02}:{s:02},{millis:03}"


def contain() -> str:
    return "scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black"


def validate_text() -> None:
    if not (len(CANONICAL) == len(TTS) == len(CAPTIONS)):
        raise SystemExit("FAIL_TEXT_CONTRACT_MISMATCH")
    visual = "\n".join(CAPTIONS)
    for item in FORBIDDEN:
        if item in visual:
            raise SystemExit(f"FAIL_FORBIDDEN_CAPTION_TOKEN:{item}")
    for item in REQUIRED:
        if item not in visual:
            raise SystemExit(f"FAIL_REQUIRED_CAPTION_TOKEN:{item}")
    if any("Binance Testnet" in item for item in CANONICAL + TTS):
        raise SystemExit("FAIL_RETIRED_TERMINOLOGY")


async def generate_narration() -> Path:
    sys.path.insert(0, str(SKILL_SCRIPTS))
    from universal_tts import generate_voice_with_meta

    output = WORK / "audio" / "narration-final-final-lock.ogg"
    path, backend = await generate_voice_with_meta(
        "\n\n".join(TTS), str(output), VOICE["voice_id"], backend="sami", allow_fallback=False, sami_retries=2
    )
    if not path or backend != "sami":
        raise SystemExit("BLOCKED_AUDIO_PROVIDER")
    if probe(Path(path), "stream=sample_rate") != "48000":
        raise SystemExit("FAIL_AUDIO_SAMPLE_RATE")
    return Path(path)


def weights() -> list[int]:
    return [max(1, len(re.sub(r"\s+", "", text))) for text in TTS]


def timed_captions(total: float) -> list[dict[str, object]]:
    w = weights()
    cursor = 0.0
    result = []
    for text, value in zip(CAPTIONS, w):
        end = cursor + total * value / sum(w)
        result.append({"text": text, "start": round(cursor, 3), "end": round(end, 3)})
        cursor = end
    return result


def write_srt(captions: list[dict[str, object]]) -> Path:
    output = WORK / "preview-final.srt"
    output.write_text("\n".join(
        f"{i}\n{ts(float(item['start']))} --> {ts(float(item['end']))}\n{item['text']}\n"
        for i, item in enumerate(captions, 1)
    ), encoding="utf-8")
    return output


def render(narration: Path, captions: list[dict[str, object]]) -> tuple[Path, list[dict[str, object]]]:
    total = duration(narration)
    scene_weights = [sum(weights()[part] for part in parts) for parts in SCENE_PARTS]
    cursor = 0.0
    parts: list[Path] = []
    scene_map = []
    for index, ((name, source_start, source_end, page), indices, weight) in enumerate(zip(SCENES, SCENE_PARTS, scene_weights)):
        target = total * weight / sum(scene_weights)
        speed = (source_end - source_start) / target
        # A screen recording remains readable only inside this deliberately modest range.
        if not 0.70 <= speed <= 1.80:
            raise SystemExit(f"FAIL_TIMING_RANGE:{name}:{speed:.2f}")
        clip = WORK / "video" / f"{index:02}-{name}.mp4"
        run(["ffmpeg", "-y", "-ss", str(source_start), "-to", str(source_end), "-i", str(SOURCE), "-vf", f"setpts=PTS/{speed:.8f},{contain()}", "-an", "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(clip)])
        parts.append(clip)
        scene_map.append({
            "narration_text": " ".join(CANONICAL[item] for item in indices),
            "caption_text": [captions[item]["text"] for item in indices],
            "output_start": round(cursor, 3), "output_end": round(cursor + target, 3),
            "source_start": source_start, "source_end": source_end, "page_name": page,
            "visual_target": page,
            "reason": "Loaded exchange view; no loading skeleton" if "exchange" in name else "Existing V8 screen area matched to locked narration.",
        })
        cursor += target
    listing = WORK / "video" / "concat.txt"
    listing.write_text("\n".join(f"file '{path.as_posix()}'" for path in parts), encoding="utf-8")
    picture = WORK / "picture-final-final-lock.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-i", str(narration), "-map", "0:v:0", "-map", "1:a:0", "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-movflags", "+faststart", str(picture)])
    return picture, scene_map


def burn(picture: Path, srt: Path) -> Path:
    final = RENDERS / "preview-final.mp4"
    escaped = srt.as_posix().replace(":", "\\:")
    subtitles = f"subtitles='{escaped}':force_style='FontName=Microsoft YaHei,FontSize=11,PrimaryColour=&HFFFFFF&,OutlineColour=&H40000000&,BorderStyle=1,Outline=1,Shadow=0,Alignment=2,MarginV=6'"
    run(["ffmpeg", "-y", "-i", str(picture), "-vf", subtitles, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "copy", "-movflags", "+faststart", str(final)])
    return final


def contact_sheet(video: Path) -> None:
    frames = WORK / "final-keyframes"
    frames.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-i", str(video), "-vf", "fps=1/5,scale=480:-1", str(frames / "frame-%03d.jpg")])
    run(["ffmpeg", "-y", "-pattern_type", "glob", "-i", str((frames / "*.jpg").as_posix()), "-filter_complex", "tile=4x4:padding=6:margin=6", "-frames:v", "1", str(RENDERS / "final-contact-sheet.jpg")])
    shutil.copytree(frames, RENDERS / "final-keyframes", dirs_exist_ok=True)


def silence_failure(audio: Path) -> bool:
    report = subprocess.check_output(["ffmpeg", "-i", str(audio), "-af", "silencedetect=n=-45dB:d=0.6", "-f", "null", "-"], stderr=subprocess.STDOUT, text=True)
    (WORK / "audio" / "silence-report.txt").write_text(report, encoding="utf-8")
    return len(re.findall(r"silence_duration: ([0-9.]+)", report)) > 5


def main() -> None:
    validate_text()
    if not SOURCE.is_file():
        raise SystemExit("Missing source recording")
    for directory in (WORK, WORK / "audio", WORK / "video", RENDERS):
        directory.mkdir(parents=True, exist_ok=True)
    (WORK / "canonical-script.md").write_text("\n\n".join(CANONICAL) + "\n", encoding="utf-8")
    (WORK / "tts-script.txt").write_text("\n\n".join(TTS) + "\n", encoding="utf-8")
    (WORK / "caption-script.json").write_text(json.dumps(CAPTIONS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    narration = asyncio.run(generate_narration())
    lock = {**VOICE, "selected_at": "2026-08-13", "source_audio_sha256": sha256(narration), "fallback": "forbidden"}
    (WORK / "audio" / "VOICE_LOCK.json").write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    captions = timed_captions(duration(narration))
    srt = write_srt(captions)
    picture, scene_map = render(narration, captions)
    final = burn(picture, srt)
    contact_sheet(final)
    (WORK / "scene-map.json").write_text(json.dumps(scene_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mechanical = silence_failure(narration)
    total = duration(final)
    status = "COMPLETE" if 60 <= total <= 68 and not mechanical else "PARTIAL"
    review = [
        "# EP01 FINAL FINAL LOCK Review", "", f"Status: {status}", "",
        f"- Duration: {total:.3f}s", f"- Voice: {VOICE['provider']} / {VOICE['voice_id']} ({VOICE['voice_name']})", "- TTS was one continuous Jianying SAMI request with fallback forbidden.",
        "- Captions came only from caption-script.json; visual tokens were scanned before rendering.",
        "- Screen recordings use FIT/CONTAIN; source page order remains frozen after the exchange cold open.",
        "- Exchange cuts start on loaded views; Why No Trade receives its own real UI segment.",
        f"- Mechanical pause check: {'FAIL_MECHANICAL_TTS_PAUSE' if mechanical else 'PASS'}.",
    ]
    if status != "COMPLETE":
        review += ["", "## Unmet Gate", "The locked full narration at the selected natural Jianying voice does not fit the simultaneous 60-68 second duration gate. It was not artificially sped up or materially rewritten."]
    (RENDERS / "final-review.md").write_text("\n".join(review) + "\n", encoding="utf-8")
    for source, target in ((srt, RENDERS / "preview-final.srt"), (WORK / "audio" / "VOICE_LOCK.json", RENDERS / "VOICE_LOCK.json"), (WORK / "scene-map.json", RENDERS / "scene-map.json")):
        shutil.copy2(source, target)
    print(json.dumps({"final": str(final), "duration": total, "status": status}, ensure_ascii=False))


if __name__ == "__main__":
    main()
