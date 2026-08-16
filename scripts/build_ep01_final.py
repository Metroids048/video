"""EP01 Final Lock.

This is a narrow V8 finish pass.  It intentionally uses the existing source
recording, FFmpeg renderer, and V7-approved voice.  It does not alter AVS
workflow/state, add a renderer, or introduce a new video style.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EP = ROOT / "episodes" / "active" / "EP-20260812-01-V2"
SOURCE = EP / "work" / "prepared" / "screen" / "20260812_131106.mp4"
WORK = EP / "work" / "final"
RENDERS = EP / "renders"
VOICE = "zh-CN-YunxiNeural"  # Project's configured natural young male voice.

# The loaded Binance cold-open is the sole source-order exception.  Once the
# recording returns to its beginning, every source span moves forward.
SCENES = [
    ("binance-hook", 128.00, 140.00, "Binance Testnet: loaded chart, balance and orders"),
    ("binance-disclaimer", 145.00, 151.80, "Binance Testnet: loaded account evidence"),
    ("maker-intro", 0.00, 14.00, "Trading workspace and project introduction"),
    ("automation-flow", 66.90, 82.00, "Opportunity decision, risk controls and orders"),
    ("why-no-trade", 84.00, 97.00, "Why No Trade in the real system UI"),
    ("research-validation", 109.30, 121.30, "Strategy research, backtest and validation"),
    ("binance-proof", 128.00, 145.00, "Binance Testnet: position, orders and balance"),
    ("next-step", 159.65, 168.00, "Local trading workspace and next step"),
]

CANONICAL = [
    "我用 AI 折腾了几个月，做了套 7×24 自动交易系统。",
    "现在它跑在 Binance Testnet 模拟盘。最开始按 5000U 作为基准，目前大概在 7350U。",
    "先说清楚，这只是模拟阶段，不代表它已经能稳定赚钱。",
    "我本职是 AI 产品经理，不会传统编程。整个项目基本都是我和 Codex、Claude Code 一点一点做出来的。",
    "它现在已经不只是一个显示买卖信号的 Demo。",
    "行情进来以后，系统会先判断有没有机会，再经过风控。条件通过才会下单，后面的持仓、订单、止盈止损和交易所状态也会继续跟踪。",
    "我自己比较在意的是这个——为什么这次没开单。是没有信号、条件没过，还是被风控拦了，系统都会把原因留下来。",
    "另一边还有策略研究、回测和验证。一个策略回测看起来不错，也不会直接扔进自动交易。",
    "后来我还给自己定了个死规则：本地有订单，不算。",
    "我会直接去 Binance 模拟盘看仓位、历史订单和账户。两边最后能对上，我才认为这条自动交易链真的跑通了。",
    "现在它还在继续跑。下一步，我主要在验证止盈止损怎么真正跟着市场状态变化。",
]

# TTS spelling is deliberately separate from both the semantic source and the
# visible captions.  Only this file may contain spoken-out number spellings.
TTS = [
    "我用 AI 折腾了几个月，做了套七乘二十四小时自动交易系统。",
    "现在它跑在 Binance Testnet 模拟盘。最开始按五千 U 作为基准，目前大概在七千三百五十 U。",
    "先说清楚，这只是模拟阶段，不代表它已经能稳定赚钱。",
    "我本职是 AI 产品经理，不会传统编程。整个项目基本都是我和 Codex、Claude Code 一点一点做出来的。",
    "它现在已经不只是一个显示买卖信号的 Demo。",
    "行情进来以后，系统会先判断有没有机会，再经过风控。条件通过才会下单，后面的持仓、订单、止盈止损和交易所状态也会继续跟踪。",
    "我自己比较在意的是这个，为什么这次没开单。是没有信号、条件没过，还是被风控拦了，系统都会把原因留下来。",
    "另一边还有策略研究、回测和验证。一个策略回测看起来不错，也不会直接扔进自动交易。",
    "后来我还给自己定了个死规则：本地有订单，不算。",
    "我会直接去 Binance 模拟盘看仓位、历史订单和账户。两边最后能对上，我才认为这条自动交易链真的跑通了。",
    "现在它还在继续跑。下一步，我主要在验证止盈止损怎么真正跟着市场状态变化。",
]

# Captions are concise, visual-first text.  They are never transcribed from
# audio and are allowed to omit speech where the system UI needs clear space.
CAPTIONS = [
    {"segment": 0, "text": "我用 AI 做了套 7×24 自动交易系统"},
    {"segment": 1, "text": "Binance Testnet · 模拟盘\n5000U 基准 -> 目前约 7350U"},
    {"segment": 2, "text": "模拟阶段 ≠ 稳定收益"},
    {"segment": 3, "text": "AI 产品经理 · Codex + Claude Code"},
    {"segment": 4, "text": "不只是买卖信号 Demo"},
    {"segment": 5, "text": "行情 -> 策略判断 -> 风控 -> 自动执行\n持仓 / 订单 / 保护 / 状态同步"},
    {"segment": 6, "text": "为什么这次没开单？\n没信号 / 条件没过 / 风控拦截"},
    {"segment": 7, "text": "策略研究 / 回测 / 验证\n回测好，不等于直接自动交易"},
    {"segment": 8, "text": "本地有单 ≠ 真实成交"},
    {"segment": 9, "text": "直接看 Binance：仓位 / 历史订单 / 账户\n两边对上，才算跑通"},
    {"segment": 10, "text": "还在继续跑\n下一步：验证止盈止损如何跟随市场"},
]

# Segment indices in the three text sources map to these visual scenes.
SCENE_SEGMENTS = [[0, 1], [2], [3, 4], [5], [6], [7], [8, 9], [10]]


def run(args: list[str]) -> None:
    subprocess.run(args, check=True)


def duration(path: Path) -> float:
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path)
    ], text=True).strip())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def timestamp(seconds: float) -> str:
    milliseconds = round(max(0.0, seconds) * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds, milliseconds = divmod(milliseconds, 1_000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def contain() -> str:
    return "scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black"


def validate_contract() -> None:
    if len(CANONICAL) != len(TTS) or len(CANONICAL) != len(CAPTIONS):
        raise SystemExit("FAIL_TEXT_CONTRACT_MISMATCH")
    if len(SCENES) != len(SCENE_SEGMENTS):
        raise SystemExit("FAIL_SCENE_CONTRACT_MISMATCH")
    for forbidden in ("七乘二十四", "五千 U", "五千U", "七千三百五十 U", "七千三百五十U"):
        if any(forbidden in item["text"] for item in CAPTIONS):
            raise SystemExit("FAIL_CAPTION_VISUAL_SPELLING")
    previous = -1.0
    for index, (_, start, end, _) in enumerate(SCENES):
        if end <= start:
            raise SystemExit("FAIL_INVALID_SOURCE_SPAN")
        if index > 1 and start < previous:
            raise SystemExit("FAIL_SOURCE_ORDER_BROKEN")
        if index > 1:
            previous = end


def voice_lock() -> dict[str, str]:
    # V7 was the existing deliberate lock and V8 retained the same identifier.
    return {
        "provider": "edge-tts",
        "voice_id": VOICE,
        "voice_name": "Yunxi Neural",
        "model": "edge-tts neural",
        "style": "default",
        "speed": "+20%",
        "pitch": "default",
        "source_version": "project default voice configuration",
        "source_audio_hash": "not applicable: newly selected from configured provider voice",
    }


def write_sources(lock: dict[str, str]) -> None:
    (WORK / "canonical-script.md").write_text("\n\n".join(CANONICAL) + "\n", encoding="utf-8")
    (WORK / "tts-script.txt").write_text("\n\n".join(TTS) + "\n", encoding="utf-8")
    (WORK / "caption-script.json").write_text(json.dumps(CAPTIONS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (WORK / "audio" / "voice-lock.json").write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def generate_continuous_narration() -> Path:
    audio = WORK / "audio" / "narration-final.mp3"
    command = [
        r"C:\Users\Windows11\.ai-workspace\venv\Scripts\python.exe", "-m", "edge_tts", "--voice", VOICE,
        "--rate=+20%", "--file", str(WORK / "tts-script.txt"), "--write-media", str(audio),
    ]
    for attempt in range(3):
        try:
            run(command)
            return audio
        except subprocess.CalledProcessError:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    raise AssertionError("unreachable")


def text_weights() -> list[float]:
    return [max(1, len(re.sub(r"\s+", "", item))) for item in TTS]


def subtitle_timing(total_duration: float) -> list[dict[str, object]]:
    weights = text_weights()
    total_weight = sum(weights)
    cursor = 0.0
    timed: list[dict[str, object]] = []
    for caption, weight in zip(CAPTIONS, weights):
        end = cursor + total_duration * weight / total_weight
        timed.append({**caption, "start": round(cursor, 3), "end": round(end, 3)})
        cursor = end
    return timed


def write_srt(timed_captions: list[dict[str, object]]) -> Path:
    srt = WORK / "preview-final.srt"
    srt.write_text("\n".join(
        f"{index}\n{timestamp(float(caption['start']))} --> {timestamp(float(caption['end']))}\n{caption['text']}\n"
        for index, caption in enumerate(timed_captions, start=1)
    ), encoding="utf-8")
    return srt


def render(timed_captions: list[dict[str, object]], narration: Path) -> tuple[Path, list[dict[str, object]]]:
    scene_weights = [sum(text_weights()[part] for part in parts) for parts in SCENE_SEGMENTS]
    total_weight = sum(scene_weights)
    audio_length = duration(narration)
    videos: list[Path] = []
    scene_map: list[dict[str, object]] = []
    output_cursor = 0.0
    for index, ((scene_id, source_start, source_end, page_name), parts, weight) in enumerate(zip(SCENES, SCENE_SEGMENTS, scene_weights)):
        target_duration = audio_length * weight / total_weight
        source_duration = source_end - source_start
        speed = source_duration / target_duration
        if not 0.70 <= speed <= 2.00:
            raise SystemExit(f"FAIL_TIMING_RANGE: {scene_id} ({speed:.2f})")
        video = WORK / "video" / f"{index:02}-{scene_id}.mp4"
        run([
            "ffmpeg", "-y", "-ss", f"{source_start:.3f}", "-to", f"{source_end:.3f}", "-i", str(SOURCE),
            "-vf", f"setpts=PTS/{speed:.8f},{contain()}", "-an", "-r", "30", "-c:v", "libx264", "-preset", "medium",
            "-crf", "18", "-pix_fmt", "yuv420p", str(video),
        ])
        videos.append(video)
        scene_map.append({
            "narration_text": " ".join(CANONICAL[part] for part in parts),
            "caption_text": [timed_captions[part]["text"] for part in parts],
            "output_start": round(output_cursor, 3),
            "output_end": round(output_cursor + target_duration, 3),
            "source_start": source_start,
            "source_end": source_end,
            "page_name": page_name,
            "visual_target": page_name,
            "reason": "Loaded Binance cold open" if index == 0 else "Source recording sequence and narration semantics are aligned.",
        })
        output_cursor += target_duration
    listing = WORK / "video" / "concat.txt"
    listing.write_text("\n".join(f"file '{video.as_posix()}'" for video in videos), encoding="utf-8")
    picture = WORK / "picture-final.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-i", str(narration), "-map", "0:v:0", "-map", "1:a:0",
         "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(picture)])
    return picture, scene_map


def burn_captions(picture: Path, srt: Path) -> Path:
    final = RENDERS / "preview-final.mp4"
    escaped = srt.as_posix().replace(":", "\\:")
    subtitles = (
        f"subtitles='{escaped}':force_style='FontName=Microsoft YaHei,FontSize=11,PrimaryColour=&HFFFFFF&,"
        "OutlineColour=&H40000000&,BorderStyle=1,Outline=1,Shadow=0,Alignment=2,MarginV=6'"
    )
    # The source is Binance's Demo Trading UI.  The explicit Chinese marker
    # makes the Testnet/simulated context readable in the final evidence shots.
    testnet_label = (
        "drawbox=x=44:y=42:w=356:h=50:color=black@0.68:t=fill:enable='between(t,0,16)+between(t,50,66)',"
        "drawtext=fontfile='C\\:/Windows/Fonts/msyhbd.ttc':text='Binance Testnet · 模拟盘':fontcolor=white:fontsize=26:"
        "x=62:y=54:enable='between(t,0,16)+between(t,50,66)'"
    )
    run(["ffmpeg", "-y", "-i", str(picture), "-vf", f"{subtitles},{testnet_label}", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "copy", "-movflags", "+faststart", str(final)])
    return final


def main() -> None:
    validate_contract()
    if not SOURCE.is_file():
        raise SystemExit("Missing source recording")
    for directory in (WORK / "audio", WORK / "video", RENDERS):
        directory.mkdir(parents=True, exist_ok=True)
    lock = voice_lock()
    write_sources(lock)
    narration = generate_continuous_narration()
    timed_captions = subtitle_timing(duration(narration))
    srt = write_srt(timed_captions)
    picture, scene_map = render(timed_captions, narration)
    final = burn_captions(picture, srt)
    (WORK / "scene-map.json").write_text(json.dumps(scene_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(srt, RENDERS / "preview-final.srt")
    shutil.copy2(WORK / "audio" / "voice-lock.json", RENDERS / "voice-lock.json")
    shutil.copy2(WORK / "scene-map.json", RENDERS / "scene-map.json")
    print(final)


if __name__ == "__main__":
    main()
