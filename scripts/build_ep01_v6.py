"""Render EP01 V6 with source pixels preserved end to end.

This is intentionally an episode-local repair.  It does not alter the source,
the workflow, or any shared renderer.  Every visual clip is FIT/CONTAIN only:
the 2556x1286 source becomes 1920x966 and is padded at y=57..1022.
"""
from __future__ import annotations

import csv
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EP = ROOT / "episodes" / "active" / "EP-20260812-01-V2"
SOURCE = EP / "work" / "prepared" / "screen" / "20260812_131106.mp4"
VOICE = EP / "work" / "v5" / "narration-yunjian-natural-pauses.m4a"
V5_SRT = EP / "work" / "v5" / "captions.srt"
WORK = EP / "work" / "v6"
RENDER = EP / "renders"

CANVAS_W, CANVAS_H = 1920, 1080
CONTENT_W, CONTENT_H, PAD_Y = 1920, 966, 57
SPEED = 1.40

# The sole non-monotonic reference is the result hook.  The main walkthrough
# always advances through the original recording, including every P0 sample.
COLD_OPEN = ("binance-result-hook", 135.50, 139.50, "Binance Testnet result")
MAIN = [
    ("dashboard", 0.00, 15.00, "主交易台 / 完整导航和 K 线"),
    ("dashboard-transition", 22.10, 35.00, "完整页面流转，覆盖 30s"),
    ("strategy-list", 55.30, 65.00, "策略库 / 列表，覆盖 60s"),
    ("risk-detail", 66.70, 76.00, "风险与详情"),
    ("why-no-trade", 83.60, 95.00, "Why No Trade，覆盖 90s"),
    ("research-validation-tab", 109.30, 124.00, "研究、验证和真实 Tab 切换，覆盖 120s"),
    ("binance-evidence", 124.75, 155.00, "Binance Demo / Positions / Order History，覆盖 150s"),
]


def run(args: list[str]) -> None:
    subprocess.run(args, check=True)


def timestamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    hour, ms = divmod(ms, 3_600_000)
    minute, ms = divmod(ms, 60_000)
    second, ms = divmod(ms, 1_000)
    return f"{hour:02}:{minute:02}:{second:02},{ms:03}"


def validate_specification() -> None:
    prior_end = -1.0
    for clip_id, start, end, _ in MAIN:
        if start < prior_end or end <= start:
            raise SystemExit(f"FAIL_SOURCE_ORDER_BROKEN: {clip_id}")
        prior_end = end
    if CONTENT_W != CANVAS_W or CONTENT_H + 2 * PAD_Y != CANVAS_H:
        raise SystemExit("FAIL_SOURCE_FRAME_CROPPED: invalid contain geometry")


def contain_filter() -> str:
    # P0: this is the only source-picture transform used by V6.  Never change
    # it to `increase`, `crop`, `cover`, or a zoom/pan expression.
    return (
        "scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black"
    )


def write_srt(path: Path) -> None:
    # Existing V5 captions already match the continuous narration timing.  V6
    # makes them smaller and parks them against the lower padding band.
    source = V5_SRT.read_text(encoding="utf-8-sig")
    path.write_text(source, encoding="utf-8")


def write_reports(parts: list[tuple[str, float, float, Path]]) -> None:
    page_rows = [
        ("0-22.10", "主交易台", "0.88-15.00", "完整导航与左/右边界保留"),
        ("22.10-55.30", "主交易台页面流转", "22.10-35.00", "连续操作，覆盖源 30s"),
        ("55.30-66.70", "策略库 / 配置列表", "55.30-65.00", "完整页面，覆盖源 60s"),
        ("66.70-83.60", "风险 / 详情", "66.70-76.00", "完整页面"),
        ("83.60-109.30", "Why No Trade", "83.60-95.00", "完整页面，覆盖源 90s"),
        ("109.30-124.75", "研究 / 验证 / Tab 切换", "109.30-124.00", "保留真实过渡，覆盖源 120s"),
        ("124.75-155.80", "Binance Demo / 仓位 / 订单", "124.75-155.00", "完整页面，覆盖源 150s"),
    ]
    report = [
        "# 页面覆盖报告 V6", "",
        "P0 已锁定为 CONTAIN/FIT：源录屏 2556x1286 被缩放至 1920x966，"
        "并在 1920x1080 母版上下各补 57px 黑边。未使用 crop、cover、zoom 或 pan。",
        "", "| 原录屏区间 | 页面 | 成片使用 | 说明 |", "|---|---|---|---|",
    ]
    report.extend(f"| {a} | {b} | {c} | {d} |" for a, b, c, d in page_rows)
    report.extend(["", "结论：Cold Open 外，source_start 单调递增；所有 P0 抽检时间点都落在主片段中。"])
    report_path = WORK / "page-coverage-report.md"
    report_path.write_text("\n".join(report), encoding="utf-8")
    (RENDER / "page-coverage-report.md").write_text("\n".join(report), encoding="utf-8")

    with (WORK / "source-output-frame-map.csv").open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["source_time_s", "clip_id", "output_time_s", "status"])
        # Source times explicitly requested by the acceptance criteria.
        checkpoints = [0.0, 10.0, 30.0, 60.0, 90.0, 120.0, 150.0]
        output_cursor = (COLD_OPEN[2] - COLD_OPEN[1]) / SPEED
        for source_time in checkpoints:
            match = next((item for item in parts if item[1] <= source_time <= item[2]), None)
            if match is None:
                raise SystemExit(f"FAIL_SOURCE_FRAME_CROPPED: P0 source checkpoint absent: {source_time}")
            _, start, _, _ = match
            output_time = output_cursor + (source_time - start) / SPEED
            writer.writerow([source_time, match[0], f"{output_time:.3f}", "PASS"])
            output_cursor = (COLD_OPEN[2] - COLD_OPEN[1]) / SPEED
            for clip_id, clip_start, clip_end, _ in parts:
                if clip_id == match[0]:
                    break
                output_cursor += (clip_end - clip_start) / SPEED


def make_comparison(parts: list[tuple[str, float, float, Path]], master: Path) -> None:
    """Create pairs: left is a source FIT reference, right is encoded output."""
    checkpoints = [0.0, 10.0, 30.0, 60.0, 90.0, 120.0, 150.0]
    pair_paths: list[Path] = []
    for index, source_time in enumerate(checkpoints, start=1):
        clip = next(item for item in parts if item[1] <= source_time <= item[2])
        clip_id, start, _, clip_path = clip
        # Decode the same source moment inside the same independently-rendered
        # clip.  No subtitle is involved, so pixel bounds are directly visible.
        offset = max(0.08, source_time - start)
        source_png = WORK / f"source-{index:02}.png"
        encoded_png = WORK / f"encoded-{index:02}.png"
        pair = WORK / f"pair-{index:02}.jpg"
        run(["ffmpeg", "-y", "-ss", f"{source_time:.3f}", "-i", str(SOURCE), "-frames:v", "1", "-vf", contain_filter(), str(source_png)])
        run(["ffmpeg", "-y", "-ss", f"{offset / SPEED:.3f}", "-i", str(clip_path), "-frames:v", "1", str(encoded_png)])
        if source_time == 10.0:
            (WORK / "source_frame.png").write_bytes(source_png.read_bytes())
            (WORK / "encoded_frame.png").write_bytes(encoded_png.read_bytes())
            (RENDER / "source_frame.png").write_bytes(source_png.read_bytes())
            (RENDER / "encoded_frame.png").write_bytes(encoded_png.read_bytes())
        run([
            "ffmpeg", "-y", "-i", str(source_png), "-i", str(encoded_png),
            "-filter_complex", "[0:v]scale=480:270[left];[1:v]scale=480:270[right];[left][right]hstack=inputs=2",
            "-frames:v", "1", str(pair),
        ])
        pair_paths.append(pair)

    inputs = []
    for pair in pair_paths:
        inputs.extend(["-i", str(pair)])
    layout = "".join(f"[{index}:v]" for index in range(len(pair_paths)))
    # 4 + 3 pairs form a compact 1920x1080 comparison sheet.
    # Two columns by four rows; the last cell is intentionally black.
    filter_graph = f"{layout}xstack=inputs=7:layout=0_0|960_0|0_270|960_270|0_540|960_540|0_810:fill=black"
    comparison = RENDER / "source-output-frame-comparison.jpg"
    run(["ffmpeg", "-y", *inputs, "-filter_complex", filter_graph, "-frames:v", "1", str(comparison)])

    # Hard, deterministic geometry check on every raw encoded clip.  A clip is
    # rejected if the required output geometry ever differs from 1920x1080.
    for clip_id, _, _, clip_path in parts:
        probe = subprocess.check_output([
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(clip_path)
        ], text=True).strip()
        if probe != "1920,1080":
            raise SystemExit(f"FAIL_SOURCE_FRAME_CROPPED: {clip_id} geometry={probe}")
    master_probe = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(master)
    ], text=True).strip()
    if master_probe != "1920,1080":
        raise SystemExit(f"FAIL_SOURCE_FRAME_CROPPED: master geometry={master_probe}")


def main() -> None:
    validate_specification()
    if not SOURCE.is_file() or not VOICE.is_file() or not V5_SRT.is_file():
        raise SystemExit("Missing source recording, continuous narration, or captions")
    WORK.mkdir(parents=True, exist_ok=True)
    RENDER.mkdir(parents=True, exist_ok=True)

    all_clips = [("cold-open",) + COLD_OPEN] + [("main",) + item for item in MAIN]
    parts: list[tuple[str, float, float, Path]] = []
    for index, (_, clip_id, start, end, _) in enumerate(all_clips):
        part = WORK / f"{index:02}-{clip_id}.mp4"
        run([
            "ffmpeg", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(SOURCE),
            "-vf", f"setpts=PTS/{SPEED},{contain_filter()}", "-an", "-r", "30",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(part),
        ])
        if clip_id != "binance-result-hook":
            parts.append((clip_id, start, end, part))

    concat = WORK / "video-parts.txt"
    concat.write_text("\n".join(f"file '{(WORK / f'{i:02}-{clip[1]}.mp4').as_posix()}'" for i, clip in enumerate(all_clips)), encoding="utf-8")
    master = WORK / "walkthrough-no-captions-v6.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-i", str(VOICE),
        "-filter_complex", "[1:a]apad=pad_dur=8[a]", "-map", "0:v:0", "-map", "[a]", "-shortest",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
        "-movflags", "+faststart", str(master),
    ])
    srt = WORK / "captions.srt"
    write_srt(srt)
    final = RENDER / "preview-final-v6.mp4"
    escaped = srt.as_posix().replace(":", "\\:")
    subtitle_filter = (
        f"subtitles='{escaped}':force_style='FontName=Microsoft YaHei,FontSize=11,"
        "PrimaryColour=&HFFFFFF&,OutlineColour=&H40000000&,BorderStyle=1,Outline=1,Shadow=0,"
        "Alignment=2,MarginV=6'"
    )
    run([
        "ffmpeg", "-y", "-i", str(master), "-vf", subtitle_filter, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "copy", "-movflags", "+faststart", str(final),
    ])
    write_reports(parts)
    make_comparison(parts, master)
    print(final)


if __name__ == "__main__":
    main()
