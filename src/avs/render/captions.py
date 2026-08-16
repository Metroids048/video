"""src/avs/render/captions.py — SRT 生成与字幕越界检测。"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from avs.freshness import write_text_if_changed
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


def _word_entries(words_path: Path) -> list[tuple[float, float, str]]:
    """Build semantic cues from final-narration word alignment data.

    The aligner is allowed to provide timing only.  It must not become an
    alternative script author, which is why every entry keeps the canonical
    ``text`` emitted by the narration stage.
    """
    payload: Any = json.loads(words_path.read_text(encoding="utf-8"))
    words = payload.get("words", payload) if isinstance(payload, dict) else payload
    if not isinstance(words, list):
        raise ValueError("final narration word timestamps must be a list or {words: [...]}")
    entries: list[tuple[float, float, str]] = []
    buffer: list[dict[str, Any]] = []
    for word in words:
        if not isinstance(word, dict):
            raise ValueError("word timestamp entry must be an object")
        text = str(word.get("text") or "").strip()
        start, end = word.get("start"), word.get("end")
        if not text or not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or end <= start:
            raise ValueError("word timestamp entry requires text, start and end")
        buffer.append({"text": text, "start": float(start), "end": float(end)})
        # Chinese narration normally has no whitespace boundaries.  Keep cues
        # short and use actual audio pauses/punctuation as natural breaks.
        joined = _join_caption_tokens([item["text"] for item in buffer])
        pause = len(buffer) > 1 and float(start) - float(buffer[-2]["end"]) >= 0.28
        boundary = text[-1:] in "。！？；，、,.!?;"
        if pause or boundary or len(joined.replace(" ", "")) >= 14:
            entries.append((buffer[0]["start"], buffer[-1]["end"], joined))
            buffer = []
    if buffer:
        entries.append((buffer[0]["start"], buffer[-1]["end"], _join_caption_tokens([item["text"] for item in buffer])))
    return entries


def _join_caption_tokens(tokens: list[str]) -> str:
    """Add readable boundaries around Latin/numeric evidence without spacing Chinese."""
    joined = ""
    for token in tokens:
        if not joined:
            joined = token
            continue
        previous = joined[-1:]
        current = token[:1]
        previous_ascii = bool(previous and previous.isascii() and previous.isalnum())
        current_ascii = bool(current and current.isascii() and current.isalnum())
        previous_cjk = bool(previous and "一" <= previous <= "鿿")
        current_cjk = bool(current and "一" <= current <= "鿿")
        if (previous_cjk and current_ascii) or (previous_ascii and current_cjk):
            joined += " "
        joined += token
    return joined


def build_srt_from_words(words_path: Path, output_path: Path, *, total_duration: float | None = None) -> int:
    """Write SRT directly from final narration alignment, never shot timing."""
    entries = _word_entries(words_path)
    if total_duration is not None:
        entries = [(start, min(end, total_duration), text) for start, end, text in entries if end > start]
    lines: list[str] = []
    for index, (start, end, text) in enumerate(entries, start=1):
        lines.extend((str(index), f"{_seconds_to_srt_time(start)} --> {_seconds_to_srt_time(end)}", format_cue_lines(text).strip(), ""))
    write_text_if_changed(output_path, "\n".join(lines))
    return len(entries)


def build_srt(timeline: Timeline, output_path: Path, *, words_path: Path | None = None) -> int:
    """从 caption 轨道提取 SRT；返回字幕条目数。

    字幕时间戳不得越界（超出 total_duration 的字幕会被截断并记录 warning）。
    """
    if words_path is not None:
        if not words_path.is_file():
            raise FileNotFoundError(f"最终旁白缺少词级对齐文件: {words_path}")
        return build_srt_from_words(words_path, output_path, total_duration=timeline.total_duration or timeline.compute_duration())
    else:
        entries = []

    caption_track = None
    for t in timeline.tracks:
        if t.kind == "caption":
            caption_track = t
            break

    if words_path is None and (caption_track is None or not caption_track.clips):
        # 无字幕轨：从脚本生成草稿（仅在无旁白时）
        logger.info("无 caption 轨道，SRT 为空")
        write_text_if_changed(output_path, "")
        return 0

    total_dur = timeline.total_duration or timeline.compute_duration()
    graphic_track = next((track for track in timeline.tracks if track.kind == "graphic"), None)
    graphic_clips = graphic_track.clips if graphic_track else []

    for clip in sorted(caption_track.clips if caption_track else [], key=lambda c: c.start):
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

    lines: list[str] = []
    for i, (s, e, text) in enumerate(entries, start=1):
        lines.append(str(i))
        lines.append(f"{_seconds_to_srt_time(s)} --> {_seconds_to_srt_time(e)}")
        clean = text.strip()
        lines.append(clean)
        lines.append("")

    # 内容未变时不刷新 mtime，否则字幕烧录层会每次都判定为过期。
    changed = write_text_if_changed(output_path, "\n".join(lines))
    logger.info(
        "SRT %s: %s  %d 条字幕", "已更新" if changed else "无变化", output_path, len(entries),
    )
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
