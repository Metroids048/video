"""Build EP01 V5 as a source-locked walkthrough.

Only the cold open may reference a later source moment. Every main-film clip is
continuous source footage and strictly advances through the original recording.
"""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EP = ROOT / "episodes" / "active" / "EP-20260812-01-V2"
SOURCE = EP / "work" / "prepared" / "screen" / "20260812_131106.mp4"
WORK = EP / "work" / "v5"
RENDER = EP / "renders"
VOICE_RAW = WORK / "narration-yunjian-continuous.mp3"
VOICE = WORK / "narration-yunjian-natural-pauses.m4a"
SPEED = 1.08

# The only deliberate source-time exception. It is a four-second result hook.
COLD_OPEN = ("cold-open-binance-balance", 135.5, 139.5, "Binance Testnet account evidence")

# Main film sequence: every interval is continuous and every start is >= the
# preceding end. Omissions are documented in the coverage report, not silently
# erased to fit narration.
MAIN = [
    ("dashboard-and-chart", 0.88, 13.88, "主交易台 / 行情与K线", "主交易台", "开场系统建立"),
    ("dashboard-to-list-transition", 22.10, 26.60, "主交易台进入列表", "真实页面切换", "保留离开交易台的真实过渡"),
    ("strategy-list", 55.30, 64.30, "策略或配置列表", "策略/配置", "展示系统不是单一信号页"),
    ("risk-and-detail", 66.70, 75.70, "风险 / 详情页面", "风险/详情", "保留进入判断与风控细节的过程"),
    ("orders-and-why-no-trade", 83.60, 92.60, "持仓订单与 Why No Trade", "Why No Trade", "核心辨识度功能"),
    ("research-validation-and-tab", 109.30, 124.00, "研究验证页面到交易所切换", "研究/验证与Tab切换", "研究辅助证明并保留切换动作"),
    ("binance-demo-orders", 124.75, 139.75, "Binance Demo 订单、持仓与余额", "Binance Testnet", "交易所优先的对账证据"),
    ("return-and-next-step", 155.80, 160.80, "返回本地系统", "返回本地系统", "阶段结论和下一步"),
]

ALL_PAGES = [
    (0.00, 22.10, "主交易台", "主交易台", True, "0.88-13.88", "保留系统开场与行情/K线"),
    (22.10, 55.30, "主交易台到列表的操作与停留", "真实过渡/重复", True, "22.10-26.60", "保留进入列表的过渡；其余为重复静态停留"),
    (55.30, 66.70, "策略或配置列表", "策略/配置", True, "55.30-64.30", "保留完整列表页"),
    (66.70, 83.60, "风险和详情", "风险/详情", True, "66.70-75.70", "保留风险/详情；尾段为重复页面停留"),
    (83.60, 109.30, "持仓订单与 Why No Trade", "Why No Trade", True, "83.60-92.60", "保留Why No Trade；其余为重复K线停留"),
    (109.30, 124.75, "研究/验证及本地到Binance切换", "研究/验证与Tab切换", True, "109.30-124.00", "保留研究辅助证明与真实切换"),
    (124.75, 155.80, "Binance Demo / Positions / Open Orders / History", "Binance Testnet", True, "124.75-139.75 + cold 135.50-139.50", "保留订单、仓位、余额；其余为重复停留"),
    (155.80, 184.09, "返回本地系统与后续计划", "返回本地系统", True, "155.80-160.80", "保留返回动作与阶段结论；其余为同屏重复"),
]

CAPTIONS = [
    (0.2, 3.6, "Binance Testnet · 模拟盘\n5000U → 约7350U"),
    (5.0, 11.0, "这是我和 Codex、Claude Code\n一轮一轮做出来的系统"),
    (18.0, 23.5, "行情 → 策略判断 → 风控 → 执行"),
    (30.0, 35.0, "持仓、订单、止盈止损\n都在同一条链路里"),
    (38.0, 42.0, "Why No Trade：为什么这一轮没有交易"),
    (47.0, 52.0, "研究、回测、验证\n不是写完策略就直接跑"),
    (59.0, 63.0, "本地有订单不算\n直接去 Binance Testnet 对账"),
    (69.0, 73.0, "账户、持仓、历史订单\n两边对上，执行链才算跑通"),
]


def run(args: list[str]) -> None:
    subprocess.run(args, check=True)


def ts(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    sec, millis = divmod(millis, 1_000)
    return f"{hours:02}:{minutes:02}:{sec:02},{millis:03}"


def validate_source_order() -> None:
    previous_end = -1.0
    for segment in MAIN:
        start, end = segment[1], segment[2]
        if start < previous_end:
            raise SystemExit("FAIL_SOURCE_ORDER_BROKEN")
        previous_end = end


def write_text_artifacts() -> None:
    page_map = []
    for start, end, page, group, used, used_time, reason in ALL_PAGES:
        page_map.append({
            "source_start": start, "source_end": end, "page_name": page,
            "page_group": group, "entered_from": None, "exited_to": None,
            "transition_type": "recorded mouse/tab/page transition",
            "important_features": [], "evidence_value": "source recording",
            "use_in_v5": used, "omit_reason": reason,
        })
    (WORK / "源录屏页面连续性地图.json").write_text(json.dumps(page_map, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 页面覆盖报告", "", "V5 使用 Source Locked Walkthrough：Cold Open 之后所有片段按原录屏时间单调递增。", "", "| 原录屏页面 | 源时间 | 是否进入成片 | 成片使用时间 | 处理原因 |", "|---|---:|---|---|---|"]
    for start, end, page, group, used, used_time, reason in ALL_PAGES:
        lines.append(f"| {page} | {start:.2f}-{end:.2f}s | {'是' if used else '否'} | {used_time} | {reason} |")
    lines.extend(["", "覆盖结论：所有重要页面组均进入成片。未使用的源时段只包含重复静态停留或等待，不因旁白未提及而删除重要页面。"])
    (WORK / "页面覆盖报告.md").write_text("\n".join(lines), encoding="utf-8")

    with (WORK / "源时间使用图.csv").open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["sequence", "kind", "clip_id", "source_start", "source_end", "source_order_valid", "note"])
        writer.writerow([0, "cold_open_exception", COLD_OPEN[0], COLD_OPEN[1], COLD_OPEN[2], "EXEMPT", "Only allowed non-monotonic source reference"])
        for index, item in enumerate(MAIN, start=1):
            writer.writerow([index, "main", item[0], item[1], item[2], "PASS", item[5]])

    (WORK / "ai音频方案说明.md").write_text(
        "# AI音频方案\n\n"
        "- 剪映/Jianying自动TTS诊断不可用，未能枚举当前账号热门音色，因此未伪称使用账号音色。\n"
        "- 实际声音：zh-CN-YunjianNeural（男性），整条旁白单次连续合成。\n"
        "- 未使用V3、V4、用户原声或音色克隆。\n"
        "- 统一将合成器产生的长静音压到自然短停顿，再做轻度响度统一。\n",
        encoding="utf-8",
    )


def write_srt(path: Path) -> None:
    chunks = []
    for index, (start, end, text) in enumerate(CAPTIONS, start=1):
        chunks.append(f"{index}\n{ts(start)} --> {ts(end)}\n{text}\n")
    path.write_text("\n".join(chunks), encoding="utf-8")


def main() -> None:
    validate_source_order()
    if not SOURCE.exists() or not VOICE_RAW.exists():
        raise SystemExit("Missing source recording or continuous TTS narration")
    WORK.mkdir(parents=True, exist_ok=True)
    RENDER.mkdir(parents=True, exist_ok=True)
    for stale in list(WORK.glob("??-*.mp4")) + [
        WORK / "walkthrough-silent.mp4", WORK / "video-parts.txt", VOICE,
    ]:
        if stale.exists():
            stale.unlink()
    # TTS is one continuous generation. This only caps generated sentence gaps,
    # avoiding the regular 0.5-0.8s cadence caused by default punctuation pauses.
    run(["ffmpeg", "-y", "-i", str(VOICE_RAW), "-af",
         "silenceremove=stop_periods=-1:stop_duration=0.20:stop_threshold=-40dB:stop_silence=0.14,"
         "loudnorm=I=-16:TP=-1.5:LRA=7", "-c:a", "aac", "-ar", "48000", "-b:a", "192k", str(VOICE)])

    ordered = [("cold",) + COLD_OPEN] + [("main",) + item for item in MAIN]
    parts: list[Path] = []
    for index, (_, clip_id, start, end, *_) in enumerate(ordered):
        output = WORK / f"{index:02}-{clip_id}.mp4"
        video_filter = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
        run(["ffmpeg", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(SOURCE),
             "-vf", video_filter, "-an", "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-pix_fmt", "yuv420p", str(output)])
        parts.append(output)

    concat = WORK / "video-parts.txt"
    concat.write_text("\n".join(f"file '{part.as_posix()}'" for part in parts), encoding="utf-8")
    assembled = WORK / "walkthrough-silent.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-i", str(VOICE),
         "-filter_complex", f"[0:v]setpts=PTS/{SPEED}[v];[1:a]apad=pad_dur=8[a]", "-map", "[v]", "-map", "[a]",
         "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-ar", "48000",
         "-b:a", "192k", "-movflags", "+faststart", str(assembled)])

    srt = WORK / "captions.srt"
    write_srt(srt)
    final = RENDER / "preview-final-v5.mp4"
    escaped_srt = srt.as_posix().replace(":", "\\:")
    subtitle_filter = (
        f"subtitles='{escaped_srt}':force_style='FontName=Microsoft YaHei,FontSize=24,"
        "PrimaryColour=&HFFFFFF&,OutlineColour=&H38000000&,BorderStyle=1,Outline=1.2,"
        "Shadow=0,Alignment=2,MarginV=54'"
    )
    run(["ffmpeg", "-y", "-i", str(assembled), "-vf", subtitle_filter, "-c:v", "libx264", "-preset", "medium",
         "-crf", "18", "-c:a", "copy", "-movflags", "+faststart", str(final)])
    shutil.copy2(srt, RENDER / "preview-final-v5.srt")
    write_text_artifacts()
    print(final)


if __name__ == "__main__":
    main()
