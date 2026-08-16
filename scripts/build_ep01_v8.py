"""V8: a focused re-edit of V7 with one narration/timeline source.

No project workflow, renderer, canvas, or voice strategy is changed here.  The
only changes are story order, narration, clip allocation, and removal of the
Binance loading span.  Screen footage always uses FIT/CONTAIN, never crop.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EP = ROOT / "episodes" / "active" / "EP-20260812-01-V2"
SOURCE = EP / "work" / "prepared" / "screen" / "20260812_131106.mp4"
WORK = EP / "work" / "v8"
RENDER = EP / "renders"
NARRATION = WORK / "narration-v8.md"
VOICE = "zh-CN-YunjianNeural"  # V7 voice is deliberately locked.

# The first item is the approved hook exception.  Every later item advances in
# source order.  124.75-127.90 is intentionally omitted: it is only loading.
SECTIONS = [
    ("exchange-hook-loaded", 128.00, 137.50, "已加载交易所模拟盘：K线、仓位、订单、余额", True),
    ("simulation-proof", 145.00, 155.00, "交易所模拟盘订单与账户", True),
    ("ai-product-manager", 0.00, 12.00, "交易台总览与 AI 产品经理身份", False),
    ("research-validation", 55.30, 64.00, "策略库、研究、回测与验证", False),
    ("automatic-flow", 66.90, 79.00, "策略判断、风控与订单", False),
    ("why-no-trade", 84.00, 96.00, "Why No Trade", False),
    ("binance-proof-loaded", 128.00, 144.50, "已加载交易所模拟盘：仓位、订单、账户", False),
    ("next-step", 159.65, 170.00, "回到本地交易台与下一步", False),
]


def run(args: list[str]) -> None:
    subprocess.run(args, check=True)


def generate_voice(text: str, output: Path) -> None:
    args = ["C:\\Users\\Windows11\\.ai-workspace\\venv\\Scripts\\python.exe", "-m", "edge_tts", "--voice", VOICE,
            "--rate=+14%", "--text", text, "--write-media", str(output)]
    for attempt in range(3):
        try:
            run(args)
            return
        except subprocess.CalledProcessError:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def duration(path: Path) -> float:
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path)
    ], text=True).strip())


def ts(seconds: float) -> str:
    ms = round(max(0.0, seconds) * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def contain() -> str:
    return "scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black"


def paragraphs() -> list[str]:
    data = [piece.strip().replace("\n", "") for piece in re.split(r"\n\s*\n", NARRATION.read_text(encoding="utf-8")) if piece.strip()]
    if len(data) != len(SECTIONS):
        raise SystemExit(f"Narration needs {len(SECTIONS)} paragraphs, got {len(data)}")
    return data


def validate_order() -> None:
    last = -1.0
    for clip_id, start, end, _, is_hook in SECTIONS:
        if end <= start:
            raise SystemExit(f"Invalid source span: {clip_id}")
        if not is_hook and start < last:
            raise SystemExit(f"FAIL_SOURCE_ORDER_BROKEN: {clip_id}")
        if not is_hook:
            last = end


def write_subtitles(texts: list[str], durations: list[float]) -> Path:
    cues: list[tuple[float, float, str]] = []
    cursor = 0.0
    for paragraph, span in zip(texts, durations):
        sentences = [line.strip() for line in re.split(r"(?<=[。！？])", paragraph) if line.strip()]
        weights = [max(1, len(line)) for line in sentences]
        total = sum(weights)
        for line, weight in zip(sentences, weights):
            end = cursor + span * weight / total
            cues.append((cursor, end, line))
            cursor = end
    srt = WORK / "captions-v8.srt"
    srt.write_text("\n".join(
        f"{n}\n{ts(start)} --> {ts(end)}\n{text}\n" for n, (start, end, text) in enumerate(cues, start=1)
    ), encoding="utf-8")
    return srt


def main() -> None:
    validate_order()
    if not SOURCE.is_file() or not NARRATION.is_file():
        raise SystemExit("Missing source recording or narration-v8.md")
    WORK.mkdir(parents=True, exist_ok=True)
    RENDER.mkdir(parents=True, exist_ok=True)
    texts = paragraphs()
    audio_parts, video_parts, narration_durations = [], [], []
    coverage = ["# 页面覆盖报告 V8", "", "V8 只重剪内容：开场与高潮均从已加载的交易所模拟盘画面开始。", "", "| 片段 | 原录屏时间 | 页面 |", "|---|---|---|"]

    for index, ((clip_id, start, end, page, _), text) in enumerate(zip(SECTIONS, texts)):
        audio = WORK / f"{index:02}-{clip_id}-v8r2.mp3"
        if not audio.is_file() or audio.stat().st_size == 0:
            generate_voice(text, audio)
        spoken = duration(audio)
        source_span = end - start
        speed = source_span / spoken
        if not 0.70 <= speed <= 1.80:
            raise SystemExit(f"Narration/video timing out of range: {clip_id} = {speed:.2f}")
        video = WORK / f"{index:02}-{clip_id}-v8.mp4"
        run(["ffmpeg", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(SOURCE), "-vf",
             f"setpts=PTS/{speed:.8f},{contain()}", "-an", "-r", "30", "-c:v", "libx264", "-preset", "medium",
             "-crf", "18", "-pix_fmt", "yuv420p", str(video)])
        audio_parts.append(audio)
        video_parts.append(video)
        narration_durations.append(spoken)
        coverage.append(f"| {clip_id} | {start:.2f}-{end:.2f}s | {page} |")

    audio_list = WORK / "audio-parts.txt"
    audio_list.write_text("\n".join(f"file '{path.as_posix()}'" for path in audio_parts), encoding="utf-8")
    narration = WORK / "narration-v8.m4a"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(audio_list), "-af", "loudnorm=I=-16:TP=-1.5:LRA=7",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", str(narration)])

    video_list = WORK / "video-parts.txt"
    video_list.write_text("\n".join(f"file '{path.as_posix()}'" for path in video_parts), encoding="utf-8")
    picture = WORK / "picture-v8.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(video_list), "-i", str(narration), "-map", "0:v:0", "-map", "1:a:0",
         "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "copy", "-movflags", "+faststart", str(picture)])

    srt = write_subtitles(texts, narration_durations)
    hook_label = WORK / "hook-label.txt"
    hook_label.write_text("交易所模拟盘  |  5000U -> 约7350U", encoding="utf-8")
    final = RENDER / "preview-final-v8.mp4"
    escaped = srt.as_posix().replace(":", "\\:")
    escaped_label = hook_label.as_posix().replace(":", "\\:")
    caption_filter = (
        f"subtitles='{escaped}':force_style='FontName=Microsoft YaHei,FontSize=11,PrimaryColour=&HFFFFFF&,"
        "OutlineColour=&H40000000&,BorderStyle=1,Outline=1,Shadow=0,Alignment=2,MarginV=6',"
        "drawbox=x=48:y=44:w=570:h=70:color=black@0.72:t=fill:enable='between(t,0,7)',"
        f"drawtext=fontfile='C\\:/Windows/Fonts/msyhbd.ttc':textfile='{escaped_label}':fontcolor=white:fontsize=28:x=68:y=64:enable='between(t,0,7)'"
    )
    run(["ffmpeg", "-y", "-i", str(picture), "-vf", caption_filter, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "copy", "-movflags", "+faststart", str(final)])
    shutil.copy2(srt, RENDER / "preview-final-v8.srt")
    (WORK / "page-coverage-report-v8.md").write_text("\n".join(coverage), encoding="utf-8")
    (RENDER / "page-coverage-report-v8.md").write_text("\n".join(coverage), encoding="utf-8")
    print(final)


if __name__ == "__main__":
    main()
