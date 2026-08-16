"""Render EP01 V7 from one editable narration source.

The narration, subtitle timing, and video sections are generated together.
This avoids the V6 error of reusing an audio/SRT pair after changing the edit.
All screen recording transforms remain FIT/CONTAIN only.
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
WORK = EP / "work" / "v7"
RENDER = EP / "renders"
NARRATION = WORK / "narration-v7.md"
VOICE = "zh-CN-YunjianNeural"

# Source order is the master timeline.  Each section has one natural narration
# paragraph and one uninterrupted screen-recording interval.
SECTIONS = [
    ("ai-product-manager", 0.00, 15.00, "AI 产品经理 / 下班后做项目"),
    ("exchange-simulation", 22.10, 40.00, "交易所模拟盘的阶段结果"),
    ("strategy-sources", 55.30, 70.00, "开源策略和交易经验"),
    ("risk-and-orders", 76.00, 90.00, "机会判断、风险和订单"),
    ("why-no-trade", 90.00, 103.00, "为什么不开单"),
    ("research-validation", 109.30, 123.00, "研究、回测和验证"),
    ("exchange-proof", 124.75, 145.00, "交易所模拟盘的仓位、订单和余额"),
]


def run(args: list[str]) -> None:
    subprocess.run(args, check=True)


def generate_voice(text: str, output: Path) -> None:
    args = ["C:\\Users\\Windows11\\.ai-workspace\\venv\\Scripts\\python.exe", "-m", "edge_tts", "--voice", VOICE,
            "--rate=+5%", "--text", text, "--write-media", str(output)]
    for attempt in range(3):
        try:
            run(args)
            return
        except subprocess.CalledProcessError:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def probe_duration(path: Path) -> float:
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path)
    ], text=True).strip())


def timestamp(seconds: float) -> str:
    ms = max(0, round(seconds * 1000))
    hour, ms = divmod(ms, 3_600_000)
    minute, ms = divmod(ms, 60_000)
    second, ms = divmod(ms, 1_000)
    return f"{hour:02}:{minute:02}:{second:02},{ms:03}"


def contain_filter() -> str:
    return (
        "scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black"
    )


def verify_source_order() -> None:
    previous = -1.0
    for clip_id, start, end, _ in SECTIONS:
        if start < previous or end <= start:
            raise SystemExit(f"FAIL_SOURCE_ORDER_BROKEN: {clip_id}")
        previous = end


def read_paragraphs() -> list[str]:
    paragraphs = [item.strip().replace("\n", "") for item in re.split(r"\n\s*\n", NARRATION.read_text(encoding="utf-8")) if item.strip()]
    if len(paragraphs) != len(SECTIONS):
        raise SystemExit(f"Narration needs {len(SECTIONS)} paragraphs; found {len(paragraphs)}")
    return paragraphs


def write_srt(paragraphs: list[str], durations: list[float]) -> Path:
    """Use exactly the spoken paragraph as its caption, max two short lines."""
    cues: list[tuple[float, float, str]] = []
    cursor = 0.0
    for text, duration in zip(paragraphs, durations):
        # Split only at natural sentence punctuation.  Every cue is spoken
        # continuously, leaving no unexplained gaps in the subtitle track.
        sentences = [piece.strip() for piece in re.split(r"(?<=[。！？])", text) if piece.strip()]
        weights = [max(1, len(item)) for item in sentences]
        total = sum(weights)
        inner = cursor
        for sentence, weight in zip(sentences, weights):
            piece_duration = duration * weight / total
            cues.append((inner, inner + piece_duration, sentence))
            inner += piece_duration
        cursor += duration
    srt = WORK / "captions-v7.srt"
    srt.write_text("\n".join(
        f"{index}\n{timestamp(start)} --> {timestamp(end)}\n{text}\n"
        for index, (start, end, text) in enumerate(cues, start=1)
    ), encoding="utf-8")
    return srt


def main() -> None:
    verify_source_order()
    if not SOURCE.is_file() or not NARRATION.is_file():
        raise SystemExit("Missing screen recording or narration-v7.md")
    WORK.mkdir(parents=True, exist_ok=True)
    RENDER.mkdir(parents=True, exist_ok=True)
    paragraphs = read_paragraphs()
    audio_parts: list[Path] = []
    video_parts: list[Path] = []
    durations: list[float] = []
    coverage = ["# 页面覆盖报告 V7", "", "V7 的旁白、字幕和画面均由 `narration-v7.md` 生成。", "", "| 旁白段落 | 源录屏片段 | 页面 |", "|---|---|---|"]

    for index, ((clip_id, start, end, page), text) in enumerate(zip(SECTIONS, paragraphs)):
        audio = WORK / f"{index:02}-{clip_id}-v7r2.mp3"
        # One TTS request per natural paragraph, never one request per sentence.
        if not audio.is_file() or audio.stat().st_size == 0:
            generate_voice(text, audio)
        duration = probe_duration(audio)
        source_duration = end - start
        speed = source_duration / duration
        if speed > 1.8 or speed < 0.7:
            raise SystemExit(f"Narration/video timing out of range for {clip_id}: {speed:.2f}")
        video = WORK / f"{index:02}-{clip_id}.mp4"
        run([
            "ffmpeg", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(SOURCE),
            "-vf", f"setpts=PTS/{speed:.8f},{contain_filter()}", "-an", "-r", "30", "-c:v", "libx264",
            "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(video),
        ])
        audio_parts.append(audio)
        video_parts.append(video)
        durations.append(duration)
        coverage.append(f"| {index + 1} | {start:.2f}-{end:.2f}s | {page} |")

    audio_list = WORK / "audio-parts.txt"
    audio_list.write_text("\n".join(f"file '{item.as_posix()}'" for item in audio_parts), encoding="utf-8")
    voice = WORK / "narration-v7.m4a"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(audio_list), "-af",
         "loudnorm=I=-16:TP=-1.5:LRA=7", "-c:a", "aac", "-ar", "48000", "-b:a", "192k", str(voice)])

    video_list = WORK / "video-parts.txt"
    video_list.write_text("\n".join(f"file '{item.as_posix()}'" for item in video_parts), encoding="utf-8")
    picture = WORK / "picture-v7.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(video_list), "-i", str(voice), "-map", "0:v:0", "-map", "1:a:0",
         "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "copy", "-movflags", "+faststart", str(picture)])

    srt = write_srt(paragraphs, durations)
    final = RENDER / "preview-final-v7.mp4"
    escaped_srt = srt.as_posix().replace(":", "\\:")
    subtitles = (
        f"subtitles='{escaped_srt}':force_style='FontName=Microsoft YaHei,FontSize=11,"
        "PrimaryColour=&HFFFFFF&,OutlineColour=&H40000000&,BorderStyle=1,Outline=1,Shadow=0,"
        "Alignment=2,MarginV=6'"
    )
    run(["ffmpeg", "-y", "-i", str(picture), "-vf", subtitles, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "copy", "-movflags", "+faststart", str(final)])
    shutil.copy2(srt, RENDER / "preview-final-v7.srt")
    (WORK / "page-coverage-report.md").write_text("\n".join(coverage), encoding="utf-8")
    (RENDER / "page-coverage-report-v7.md").write_text("\n".join(coverage), encoding="utf-8")
    print(final)


if __name__ == "__main__":
    main()
