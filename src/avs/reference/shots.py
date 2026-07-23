"""src/avs/reference/shots.py — 镜头边界检测。

优先使用 ffprobe scene detection；不可用时退化为单镜头。
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

_SCENE_THRESHOLD = 0.35   # 场景变化阈值（0-1）


@dataclass
class Shot:
    shot_id: str
    start: float      # 秒
    end: float        # 秒
    keyframe_path: str | None = None
    transcript: str | None = None
    shot_type: str | None = None
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "shot_id": self.shot_id,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "keyframe_path": self.keyframe_path,
            "transcript": self.transcript,
            "shot_type": self.shot_type,
            "confidence": round(self.confidence, 3),
        }


def detect_shots(
    video_path: Path,
    duration: float,
    *,
    threshold: float = _SCENE_THRESHOLD,
    timeout: int = 60,
) -> list[Shot]:
    """返回镜头列表；FFprobe/FFmpeg 不可用时返回单镜头。"""
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        log.warning("ffmpeg/ffprobe 不可用，退化为单镜头: %s", video_path.name)
        return _single_shot(duration)

    boundaries = _detect_boundaries(video_path, threshold=threshold, timeout=timeout)
    if not boundaries:
        return _single_shot(duration)

    return _boundaries_to_shots(boundaries, duration)


def _detect_boundaries(video_path: Path, *, threshold: float, timeout: int) -> list[float]:
    """用 ffmpeg select filter 获取场景变化时间戳列表（秒）。"""
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", f"select='gt(scene,{threshold})',metadata=print:file=-",
        "-an", "-f", "null", "-",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        log.warning("镜头检测超时: %s", video_path.name)
        return []

    # 解析 "pts_time:X.XXX" 行
    timestamps: list[float] = []
    for line in result.stdout.splitlines() + result.stderr.splitlines():
        if "pts_time:" in line:
            try:
                t = float(line.split("pts_time:")[1].split()[0])
                timestamps.append(t)
            except (IndexError, ValueError):
                pass

    return sorted(set(timestamps))


def _boundaries_to_shots(boundaries: list[float], duration: float) -> list[Shot]:
    """将时间戳列表转换为 Shot 对象列表。"""
    # 第一个镜头从 0 开始
    starts = [0.0] + boundaries
    ends = boundaries + [duration]

    shots: list[Shot] = []
    for i, (s, e) in enumerate(zip(starts, ends)):
        if e - s < 0.1:       # 过短的镜头跳过
            continue
        shots.append(Shot(
            shot_id=f"s{i+1:03d}",
            start=s,
            end=e,
            confidence=0.85,  # ffmpeg scene detection 置信度中等
        ))
    return shots or _single_shot(duration)


def _single_shot(duration: float) -> list[Shot]:
    """无法检测时返回跨越全视频的单镜头。"""
    return [Shot(shot_id="s001", start=0.0, end=max(duration, 0.001), confidence=0.5)]
