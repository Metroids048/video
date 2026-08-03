"""src/avs/render/captions.py — SRT 生成与字幕越界检测。"""
from __future__ import annotations

import logging
from pathlib import Path

from avs.timeline.models import Timeline
from avs.render.caption_segmentation import format_cue_lines, segment_caption

logger = logging.getLogger(__name__)


def _seconds_to_srt_time(s: float) -> str:
    """将秒数转换为 SRT 时间格式 HH:MM:SS,mmm。"""
    hours = int(s // 3600)
    minutes = int((s % 3600) // 60)
    secs = int(s % 60)
    ms = int(round((s % 1) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def build_srt(timeline: Timeline, output_path: Path) -> int:
    """从 caption 轨道提取 SRT；返回字幕条目数。

    字幕时间戳不得越界（超出 total_duration 的字幕会被截断并记录 warning）。
    """
    caption_track = None
    for t in timeline.tracks:
        if t.kind == "caption":
            caption_track = t
            break

    if caption_track is None or not caption_track.clips:
        # 无字幕轨：从脚本生成草稿（仅在无旁白时）
        logger.info("无 caption 轨道，SRT 为空")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("", encoding="utf-8")
        return 0

    total_dur = timeline.total_duration or timeline.compute_duration()
    entries: list[tuple[float, float, str]] = []
    graphic_track = next((track for track in timeline.tracks if track.kind == "graphic"), None)
    graphic_clips = graphic_track.clips if graphic_track else []

    for clip in sorted(caption_track.clips, key=lambda c: c.start):
        text = clip.text or ""
        if not text.strip():
            continue
        if any(
            abs(graphic.start - clip.start) < 0.01
            and abs(graphic.duration - clip.duration) < 0.01
            and (graphic.text or "").strip() == text.strip()
            for graphic in graphic_clips
        ):
            continue
        start = clip.start
        end = clip.end

        # 越界截断
        if end > total_dur + 0.05:
            logger.warning("字幕越界截断: clip_id=%s end=%.3f > total=%.3f",
                           clip.clip_id, end, total_dur)
            end = total_dur

        if end <= start:
            continue
        for cue in segment_caption(text, start, end):
            entries.append((cue.start, cue.end, format_cue_lines(cue.text)))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for i, (s, e, text) in enumerate(entries, start=1):
        lines.append(str(i))
        lines.append(f"{_seconds_to_srt_time(s)} --> {_seconds_to_srt_time(e)}")
        clean = text.strip()
        lines.append(clean)
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("SRT 已生成: %s  %d 条字幕", output_path, len(entries))
    return len(entries)


def has_subtitle_overflow(srt_path: Path, total_duration: float) -> list[str]:
    """检测 SRT 中是否有字幕时间超出 total_duration，返回违规 entry 号列表。"""
    violations: list[str] = []
    if not srt_path.exists():
        return violations

    content = srt_path.read_text(encoding="utf-8")
    for block in content.strip().split("\n\n"):
        lines_b = [line.strip() for line in block.strip().splitlines()]
        if len(lines_b) < 2:
            continue
        idx = lines_b[0]
        ts_line = lines_b[1] if len(lines_b) > 1 else ""
        if "-->" not in ts_line:
            continue
        end_str = ts_line.split("-->")[1].strip()
        try:
            h, m, s_ms = end_str.split(":")
            s, ms = s_ms.split(",")
            end_s = int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000
            if end_s > total_duration + 0.05:
                violations.append(idx)
        except Exception:
            pass
    return violations
