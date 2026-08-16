"""Render EP01 V4 as an original-recording-led system walkthrough.

This is intentionally episode-local. It creates no new production pipeline and
does not alter the original recording: each published segment is a working copy
of a continuous source interval, kept in the order in which it was recorded.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EP = ROOT / "episodes" / "active" / "EP-20260812-01-V2"
SOURCE = EP / "work" / "prepared" / "screen" / "20260812_131106.mp4"
WORK = EP / "work" / "v4"
RENDER = EP / "renders"
SPEED = 1.5

# Source order is the master timeline. The trimmed gaps only remove filler and
# silence; they never reorder the walkthrough or replace its evidence.
SEGMENTS = [
    ("system-intro", 0.88, 16.70, "系统总览：7×24小时自动交易系统，以及由 Codex 和 Claude Code 协作构建。"),
    ("simulation-result", 20.52, 32.42, "模拟盘从约 5000U 跑到约 7300U。"),
    ("simulation-caveat", 35.88, 41.70, "这是模拟盘阶段结果，不证明策略能稳定赚钱。"),
    ("strategy-research", 52.58, 65.88, "连续进入策略库、模型和知识库。"),
    ("decision-risk", 74.72, 85.12, "策略判断经过风控，再自动开平仓和挂保护单。"),
    ("why-no-trade", 87.38, 93.94, "Why No Trade 解释为何这一轮没有开单。"),
    ("research-validation", 103.46, 117.70, "研究、验证和执行被串成同一条交易闭环。"),
    ("binance-tab-proof", 119.84, 144.50, "保留从本地系统切到 Binance Testnet，并查看订单、余额和仓位对账的真实过程。"),
    ("next-step", 154.14, 168.76, "下一步继续用样本、回撤、手续费和市场信息改进订单设置。"),
]


def run(args: list[str]) -> None:
    subprocess.run(args, check=True)


def timestamp(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1_000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def write_captions(path: Path) -> None:
    captions = [
        "一套能 7×24 小时运行的自动交易系统",
        "模拟盘从约 5000U 跑到约 7300U",
        "这是模拟盘阶段结果，不代表策略稳定赚钱",
        "实时行情、策略库、模型和知识库",
        "策略判断后，再经过风控执行",
        "Why No Trade：为什么这次没有开单",
        "研究、验证、执行，串成同一条交易闭环",
        "本地系统 → Binance Testnet：订单、余额、仓位对账",
        "下一步继续用样本、回撤、手续费改进订单设置",
    ]
    cursor = 0.0
    blocks: list[str] = []
    for index, ((_, start, end, _), caption) in enumerate(zip(SEGMENTS, captions), start=1):
        duration = (end - start) / SPEED
        # Evidence-heavy scenes get room to be read without captions competing.
        shown = min(duration - 0.45, 5.4) if index not in {6, 8} else min(duration - 1.2, 3.8)
        blocks.append(f"{index}\n{timestamp(cursor + 0.25)} --> {timestamp(cursor + shown)}\n{caption}\n")
        cursor += duration
    path.write_text("\n".join(blocks), encoding="utf-8")


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"Missing prepared recording: {SOURCE}")
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    RENDER.mkdir(parents=True, exist_ok=True)

    parts: list[Path] = []
    for index, (segment_id, start, end, _) in enumerate(SEGMENTS):
        part = WORK / f"{index:02}-{segment_id}.mp4"
        # The source is slightly wider than 16:9. This preserves its full height
        # and only trims the narrow side margins; no blurred background or cards.
        vf = (
            f"setpts=PTS/{SPEED},"
            "scale=1920:1080:force_original_aspect_ratio=increase,"
            "crop=1920:1080"
        )
        af = (
            f"atempo={SPEED},"
            "highpass=f=80,lowpass=f=15500,"
            "afftdn=nf=-28,acompressor=threshold=-20dB:ratio=2.2:attack=12:release=160,"
            "loudnorm=I=-16:TP=-1.5:LRA=7"
        )
        run([
            "ffmpeg", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(SOURCE),
            "-filter_complex", f"[0:v]{vf}[v];[0:a]{af}[a]",
            "-map", "[v]", "-map", "[a]", "-r", "30", "-c:v", "libx264", "-preset", "medium",
            "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-b:a", "192k", str(part),
        ])
        parts.append(part)

    concat = WORK / "parts.txt"
    concat.write_text("\n".join(f"file '{part.as_posix()}'" for part in parts), encoding="utf-8")
    picture = WORK / "picture-and-original-voice.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy",
        "-movflags", "+faststart", str(picture),
    ])

    srt = WORK / "captions.srt"
    write_captions(srt)
    final = RENDER / "preview-final-v4.mp4"
    subtitle_path = srt.as_posix().replace(":", "\\:")
    subtitle_filter = (
        f"subtitles='{subtitle_path}':"
        "force_style='FontName=Microsoft YaHei,FontSize=24,PrimaryColour=&HFFFFFF&,"
        "OutlineColour=&H38000000&,BorderStyle=1,Outline=1.2,Shadow=0,Alignment=2,MarginV=54'"
    )
    run([
        "ffmpeg", "-y", "-i", str(picture), "-vf", subtitle_filter, "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-c:a", "copy", "-movflags", "+faststart", str(final),
    ])

    continuity = {
        "episode_id": "EP-20260812-01-V2",
        "version": "v4",
        "master_source": str(SOURCE.relative_to(EP)).replace("\\", "/"),
        "audio_strategy": "AUDIO_A",
        "speed": SPEED,
        "rules": [
            "All published scenes retain the source recording order.",
            "Each segment is a continuous source interval; cuts remove filler and silence only.",
            "The Binance transition is retained as a real tab change, not substituted with a screenshot.",
        ],
        "segments": [
            {"id": sid, "source_start": start, "source_end": end, "published_duration": round((end - start) / SPEED, 3), "purpose": purpose}
            for sid, start, end, purpose in SEGMENTS
        ],
    }
    (WORK / "页面连续性地图.json").write_text(json.dumps(continuity, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(srt, RENDER / "preview-final-v4.srt")
    print(final)


if __name__ == "__main__":
    main()
