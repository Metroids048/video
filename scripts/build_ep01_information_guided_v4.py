"""Build EP01's information-guided V4 from the real source recording.

The locked V3 audio is preserved. The visual edit is rebuilt from continuous
source-recording intervals with fixed ROIs; no Ken Burns, animated crop, fake
cursor, generated evidence, split-screen, or TTS regeneration is used.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import NamedTuple


TARGET_VIDEO_BITRATE = "8M"
TARGET_VIDEO_MINRATE = "8M"
TARGET_VIDEO_MAXRATE = "8M"
X264_CBR_PARAMS = "nal-hrd=cbr:filler=1"


BLOCKING_STATUS_NAMES = (
    "TECHNICAL",
    "VISUAL_CONTINUITY",
    "MOBILE_READABILITY",
    "SUBTITLE",
    "AUDIO",
    "AUDIO_VISUAL_SEMANTIC_SYNC",
    "CONTENT",
)


class Segment(NamedTuple):
    name: str
    source_kind: str
    source_start: float
    source_end: float
    out_start: float
    out_end: float
    crop_x: int
    crop_y: int
    crop_w: int
    crop_h: int
    purpose: str


class Overlay(NamedTuple):
    text: str
    start: float
    end: float
    style: str


def build_segments(master_duration: float) -> list[Segment]:
    # Output boundaries deliberately land on V3's measured low-energy windows:
    # ~4.17-4.44, 8.95-9.21, 15.62-15.86, 26.91-27.15, 34.32-34.53.
    end = round(master_duration, 3)
    if end < 39.45:
        raise ValueError(f"master audio unexpectedly short: {end:.3f}s")
    return [
        Segment(
            "binance-guided-tabs", "raw", 128.00, 132.32, 0.00, 4.32,
            550, 0, 900, 1286,
            "Real Binance Demo recording; mouse/tab activity guides the viewer through order evidence.",
        ),
        Segment(
            "binance-demo-result", "raw", 132.32, 134.70, 4.32, 6.70,
            1650, 0, 900, 1286,
            "Real Binance account/order-book ROI holds the demo result only long enough to read it.",
        ),
        Segment(
            "binance-demo-history-progress", "raw", 134.70, 137.05, 6.70, 9.05,
            550, 0, 900, 1286,
            "Same Binance session advances back to chart/history context instead of freezing on the result.",
        ),
        Segment(
            "local-state-proof", "raw", 76.50, 78.90, 9.05, 11.45,
            1650, 0, 900, 1286,
            "Local system state shows unfilled orders / risk state / Why No Trade evidence before exchange verification.",
        ),
        Segment(
            "binance-history-proof", "raw", 130.50, 134.80, 11.45, 15.75,
            0, 0, 900, 1286,
            "Real Binance history-area interaction; cursor and order/history tabs are visible.",
        ),
        Segment(
            "why-no-trade-scroll", "raw", 80.00, 85.59, 15.75, 21.34,
            1650, 0, 900, 1286,
            "Real Why No Trade page: cursor enters the evidence area and the page naturally scrolls through reasons and risk state.",
        ),
        Segment(
            "exchange-rejection-proof", "raw", 112.00, 117.69, 21.34, 27.03,
            700, 0, 900, 1286,
            "Real current-exchange-order evidence shows acknowledged/rejected statuses before the live dashboard advances.",
        ),
        Segment(
            "strategy-library-to-entry", "raw", 64.80, 67.00, 27.03, 29.23,
            0, 0, 900, 1286,
            "Real strategy-library context advances into the entry-logic tab.",
        ),
        Segment(
            "strategy-entry-proof", "raw", 67.00, 69.70, 29.23, 31.93,
            0, 0, 900, 1286,
            "Entry logic is shown long enough to establish a real rule system without lingering on parameters.",
        ),
        Segment(
            "strategy-exit-proof", "raw", 70.10, 72.59, 31.93, 34.42,
            0, 0, 900, 1286,
            "Real exit logic shows protective TP/SL and trailing-stop-only-tightens rules.",
        ),
        Segment(
            "binance-dynamic-exit", "raw", 129.00, 134.08, 34.42, end,
            1450, 0, 1100, 1286,
            "Real Binance Demo position / TP-SL / account area changes state while the live market remains visible for the closing question.",
        ),
    ]


def validate_segments(segments: list[Segment], master_duration: float) -> None:
    if not segments:
        raise ValueError("no visual segments")
    tol = 0.015
    if abs(segments[0].out_start) > tol:
        raise ValueError("visual timeline does not start at zero")
    for prev, cur in zip(segments, segments[1:]):
        if abs(prev.out_end - cur.out_start) > tol:
            raise ValueError(f"visual gap/overlap between {prev.name} and {cur.name}")
    if abs(segments[-1].out_end - master_duration) > 0.05:
        raise ValueError("visual timeline does not cover locked audio")
    for seg in segments:
        if seg.out_end <= seg.out_start or seg.source_end <= seg.source_start:
            raise ValueError(f"invalid duration: {seg.name}")
        if seg.crop_w <= 0 or seg.crop_h <= 0:
            raise ValueError(f"invalid crop: {seg.name}")
        speed = (seg.source_end - seg.source_start) / (seg.out_end - seg.out_start)
        if not 0.90 <= speed <= 1.10:
            raise ValueError(f"forbidden artificial speed change {seg.name}: {speed:.3f}")


def build_chapters() -> list[Overlay]:
    return [
        Overlay("真的跑起来了", 0.08, 1.55, "Top"),
        Overlay("本地有单 ≠ 真成交", 9.05, 10.55, "Top"),
        Overlay("该不下单时不下单", 15.75, 17.25, "Top"),
        Overlay("我定规则，Agent 实现", 27.03, 28.55, "Top"),
        Overlay("下一步：动态止盈", 34.42, 35.92, "Top"),
    ]


def build_labels() -> list[Overlay]:
    return [Overlay("模拟盘 · 5000U → 约7350U", 4.32, 9.05, "Tag")]


def build_captions() -> list[Overlay]:
    return [
        Overlay("我没手写代码，但它真的跑起来了", 0.39, 4.17, "Bottom"),
        Overlay("模拟盘：5000U → 约7350U", 4.44, 8.95, "Bottom"),
        Overlay("本地有单，不代表交易所真的成交", 9.21, 12.13, "Bottom"),
        Overlay("最后只认 Binance 的真实状态", 12.36, 15.62, "Bottom"),
        Overlay("自动交易最难的，不是学会下单", 15.86, 21.11, "Bottom"),
        Overlay("而是该不下单的时候，真的不下单", 21.34, 26.91, "Bottom"),
        Overlay("规则、流程、验收：我来定", 27.15, 30.99, "Bottom"),
        Overlay("Codex + Claude Code：负责实现", 31.26, 34.32, "Bottom"),
        Overlay("下一步：验证动态止盈", 34.53, 36.50, "Bottom"),
        Overlay("会不会让我提前下车？", 36.50, 39.30, "Bottom"),
    ]


def publishable_status(statuses: dict[str, str]) -> str:
    return "PASS" if all(statuses.get(name) == "PASS" for name in BLOCKING_STATUS_NAMES) else "FAIL"


def run(args: list[str], capture: bool = False) -> str:
    proc = subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None)
    return proc.stdout if capture else ""


def probe_duration(path: Path) -> float:
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nw=1:nk=1", str(path)], capture=True)
    return float(out.strip())


def ass_time(seconds: float) -> str:
    cs = max(0, round(seconds * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def _ass_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def write_ass(path: Path, duration: float) -> None:
    overlays = build_chapters() + build_labels() + build_captions()
    for item in overlays:
        if item.end > duration + 0.05:
            raise ValueError(f"overlay exceeds master: {item}")
    header = r"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Top,Noto Sans CJK SC,64,&H00FFFFFF,&H00FFFFFF,&H50000000,&H00000000,-1,0,0,0,100,100,0,0,1,2.2,0,8,56,56,48,1
Style: Bottom,Noto Sans CJK SC,52,&H00FFFFFF,&H00FFFFFF,&H20000000,&H9A000000,-1,0,0,0,100,100,0,0,3,0,0,2,72,72,238,1
Style: Tag,Noto Sans CJK SC,42,&H0000E5FF,&H0000E5FF,&H70000000,&H9A000000,-1,0,0,0,100,100,0,0,3,0,0,8,72,72,150,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    lines = [header]
    for item in sorted(overlays, key=lambda x: (x.start, x.style)):
        lines.append(f"Dialogue: 0,{ass_time(item.start)},{ass_time(item.end)},{item.style},,0,0,0,,{_ass_escape(item.text)}\n")
    path.write_text("".join(lines), encoding="utf-8")


def render_segment(seg: Segment, raw: Path, v3: Path, output: Path) -> None:
    source = raw if seg.source_kind == "raw" else v3
    out_dur = seg.out_end - seg.out_start
    src_dur = seg.source_end - seg.source_start
    speed = src_dur / out_dur
    scaled_h = round(seg.crop_h * 1080 / seg.crop_w)
    if scaled_h > 1760:
        scaled_h = 1760
    pad_y = (1920 - scaled_h) // 2
    vf = (f"crop={seg.crop_w}:{seg.crop_h}:{seg.crop_x}:{seg.crop_y},"
          f"setpts=(PTS-STARTPTS)/{speed:.8f},scale=1080:{scaled_h}:flags=lanczos,"
          f"pad=1080:1920:0:{pad_y}:color=black,fps=30,format=yuv420p")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{seg.source_start:.3f}", "-to", f"{seg.source_end:.3f}", "-i", str(source),
         "-an", "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)])


def build_video(raw: Path, v3: Path, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    work = out_dir / "work"
    if work.exists():
        shutil.rmtree(work)
    (work / "segments").mkdir(parents=True)
    duration = probe_duration(v3)
    segments = build_segments(duration)
    validate_segments(segments, duration)
    rendered = []
    for index, seg in enumerate(segments):
        part = work / "segments" / f"{index:02d}-{seg.name}.mp4"
        render_segment(seg, raw, v3, part)
        rendered.append(part)
    concat = work / "concat.txt"
    concat.write_text("\n".join(f"file '{p.as_posix()}'" for p in rendered), encoding="utf-8")
    picture = work / "picture.mp4"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(picture)])
    ass = out_dir / "EP01_V4_subtitles.ass"
    write_ass(ass, duration)
    final = out_dir / "EP01_FINAL_镜头内部信息引导重制版_v4.mp4"
    ass_filter = ass.as_posix().replace(":", r"\:")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(picture), "-i", str(v3),
         "-map", "0:v:0", "-map", "1:a:0", "-vf", f"ass='{ass_filter}'",
         "-c:v", "libx264", "-preset", "slow", "-b:v", TARGET_VIDEO_BITRATE,
         "-minrate", TARGET_VIDEO_MINRATE, "-maxrate", TARGET_VIDEO_MAXRATE, "-bufsize", "16M",
         "-x264-params", X264_CBR_PARAMS, "-profile:v", "high", "-level", "4.1",
         "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
         "-t", f"{duration:.3f}", "-movflags", "+faststart", str(final)])
    mobile = out_dir / "EP01_V4_手机预览_360x640.mp4"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(final),
         "-vf", "scale=360:640:flags=lanczos", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-movflags", "+faststart", str(mobile)])
    timeline = out_dir / "EP01_V4_timeline.json"
    timeline.write_text(json.dumps({
        "version": "EP01_INFORMATION_GUIDED_V4", "audio_master": str(v3), "visual_master": str(raw),
        "duration": round(duration, 3),
        "rules": {"tts_regenerated": False, "animated_zoom_pan": False, "fake_cursor": False,
                  "generated_evidence": False, "split_screen": False, "fixed_roi_only": True,
                  "chapter_title_max_seconds": 1.8},
        "segments": [seg._asdict() for seg in segments],
        "chapters": [item._asdict() for item in build_chapters()],
        "labels": [item._asdict() for item in build_labels()],
        "captions": [item._asdict() for item in build_captions()],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"final": final, "mobile": mobile, "ass": ass, "timeline": timeline, "work": work}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--v3", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.raw, args.v3):
        if not path.is_file():
            raise SystemExit(f"missing input: {path}")
    outputs = build_video(args.raw, args.v3, args.out_dir)
    print(json.dumps({k: str(v) for k, v in outputs.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
