"""Semantic caption segmentation for readability.

根据 PAT-011 规则：
- 每 cue 最多 24 个中文字符
- 每行最多 14 个中文字符
- 最多 2 行
- cue 时长 0.8-3.5 秒
- 阅读速度不超过 12 字/秒
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class CaptionCue:
    """单个字幕 cue。"""

    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def char_count(self) -> int:
        """统计中文字符数（不含标点和空格）。"""
        return len([c for c in self.text if "一" <= c <= "鿿"])


def _count_cjk_chars(text: str) -> int:
    """统计中文字符数（不含标点和空格）。"""
    return len([c for c in text if "一" <= c <= "鿿"])


def _split_by_punctuation(text: str) -> list[str]:
    """按标点符号分句。"""
    # 中文句子结束符号
    pattern = r"[。！？；，、：]+"
    segments = re.split(pattern, text)
    return [s.strip() for s in segments if s.strip()]


def segment_caption(
    text: str,
    start: float,
    end: float,
    *,
    max_chars_per_cue: int = 24,
    max_chars_per_line: int = 14,
    max_lines: int = 2,
    min_cue_seconds: float = 0.8,
    max_cue_seconds: float = 3.5,
) -> list[CaptionCue]:
    """将长字幕文本按语义分段为多个 cue。

    Args:
        text: 完整字幕文本
        start: 开始时间（秒）
        end: 结束时间（秒）
        max_chars_per_cue: 每个 cue 最多中文字符数
        max_chars_per_line: 每行最多中文字符数
        max_lines: 最多行数
        min_cue_seconds: 最小 cue 时长
        max_cue_seconds: 最大 cue 时长

    Returns:
        分段后的 cue 列表
    """
    text = text.strip()
    if not text:
        return []

    total_duration = end - start
    cjk_count = _count_cjk_chars(text)

    # 如果已经符合单个 cue 限制，直接返回
    if cjk_count <= max_chars_per_cue and total_duration >= min_cue_seconds:
        return [CaptionCue(start, end, text)]

    # 按标点分句
    sentences = _split_by_punctuation(text)
    if not sentences or (len(sentences) == 1 and cjk_count > max_chars_per_cue):
        # 无标点或单句过长，强制按字符数切分
        sentences = [text[i : i + max_chars_per_cue] for i in range(0, len(text), max_chars_per_cue)]

    # 合并短句，分配时长
    cues: list[CaptionCue] = []
    current_text = ""
    current_char_count = 0

    for sentence in sentences:
        sentence_chars = _count_cjk_chars(sentence)

        # 如果当前累积 + 这句会超限，先输出当前 cue
        if current_text and (current_char_count + sentence_chars > max_chars_per_cue):
            # 计算这个 cue 的时长（按字符比例）
            cue_ratio = current_char_count / cjk_count if cjk_count > 0 else 1.0 / len(sentences)
            cue_duration = total_duration * cue_ratio
            cue_duration = max(min_cue_seconds, min(cue_duration, max_cue_seconds))

            cue_start = start
            cue_end = min(start + cue_duration, end)

            cues.append(CaptionCue(cue_start, cue_end, current_text))

            # 更新 start 为下一个 cue
            start = cue_end
            current_text = ""
            current_char_count = 0

        # 累积当前句子
        if current_text:
            current_text += sentence
        else:
            current_text = sentence
        current_char_count += sentence_chars

    # 输出最后一个 cue
    if current_text:
        cues.append(CaptionCue(start, end, current_text))

    return cues


def format_cue_lines(text: str, max_chars_per_line: int = 14, max_lines: int = 2) -> str:
    """将字幕文本按行数和每行字符数格式化。

    Args:
        text: 字幕文本
        max_chars_per_line: 每行最多字符数
        max_lines: 最多行数

    Returns:
        格式化后的多行文本
    """
    text = text.strip()
    if not text:
        return ""

    # 如果已经符合单行限制
    if _count_cjk_chars(text) <= max_chars_per_line:
        return text

    parts = _split_by_punctuation(text)
    compact = "".join(parts) if parts else text
    lines: list[str] = []
    current = ""
    current_units = 0
    for char in compact:
        units = 1 if ("一" <= char <= "鿿" or not char.isspace()) else 0
        if current and current_units + units > max_chars_per_line:
            lines.append(current)
            current = ""
            current_units = 0
        current += char
        current_units += units
    if current:
        lines.append(current)
    return "\n".join(lines[:max_lines])


def check_caption_quality(cue: CaptionCue, *, max_cjk_per_second: float = 12.0) -> list[str]:
    """检查字幕质量问题。

    Args:
        cue: 字幕 cue
        max_cjk_per_second: 最大中文字符/秒阅读速度

    Returns:
        问题列表（空列表表示无问题）
    """
    issues: list[str] = []

    char_count = cue.char_count
    duration = cue.duration

    if duration <= 0:
        issues.append("时长为零")
        return issues

    # 检查阅读速度
    reading_speed = char_count / duration
    if reading_speed > max_cjk_per_second:
        issues.append(f"阅读速度过快: {reading_speed:.1f} 字/秒 (最大 {max_cjk_per_second})")

    # 检查时长
    if duration < 0.8:
        issues.append(f"时长过短: {duration:.1f}s (最小 0.8s)")
    elif duration > 3.5:
        issues.append(f"时长过长: {duration:.1f}s (最大 3.5s)")

    # 检查字符数
    if char_count > 24:
        issues.append(f"字符数过多: {char_count} 字 (最大 24)")

    return issues
