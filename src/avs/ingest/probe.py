"""src/avs/ingest/probe.py — FFprobe 媒体探测（ffprobe 不可用时优雅降级）。"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


def probe_media(path: Path, timeout: int = 30) -> dict[str, Any]:
    """用 ffprobe 探测媒体文件，返回标准化元数据字典。

    返回字段：
        duration      : float | None  — 时长（秒）
        width         : int | None    — 视频宽度
        height        : int | None    — 视频高度
        fps           : float | None  — 帧率
        has_audio     : bool | None   — 是否有音频轨
        codec_video   : str | None    — 视频编码
        codec_audio   : str | None    — 音频编码
        decodable     : bool          — 能否正常解码
        ffprobe_skipped : bool        — ffprobe 不可用时为 True
        error         : str | None    — 错误原因（损坏时）
    """
    if not _ffprobe_available():
        return {
            "duration": None, "width": None, "height": None,
            "fps": None, "has_audio": None, "codec_video": None,
            "codec_audio": None, "decodable": None,
            "ffprobe_skipped": True, "error": None,
        }

    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        str(path),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return _error_result("ffprobe 超时")
    except Exception as exc:
        return _error_result(f"ffprobe 调用异常: {exc}")

    if result.returncode != 0:
        return _error_result(f"ffprobe 非零退出: {result.stderr[:200]}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return _error_result(f"ffprobe 输出解析失败: {exc}")

    return _parse_ffprobe(data)


def _error_result(reason: str) -> dict[str, Any]:
    return {
        "duration": None, "width": None, "height": None,
        "fps": None, "has_audio": None, "codec_video": None,
        "codec_audio": None, "decodable": False,
        "ffprobe_skipped": False, "error": reason,
    }


def _parse_ffprobe(data: dict) -> dict[str, Any]:
    streams = data.get("streams", [])
    fmt = data.get("format", {})

    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    vs = video_streams[0] if video_streams else None
    aus = audio_streams[0] if audio_streams else None

    # 时长：优先 format，其次 video stream
    duration: float | None = None
    raw_dur = fmt.get("duration") or (vs.get("duration") if vs else None)
    if raw_dur is not None:
        try:
            duration = float(raw_dur)
        except (TypeError, ValueError):
            pass

    # 帧率
    fps: float | None = None
    if vs:
        r_frame = vs.get("r_frame_rate", "")
        try:
            num, den = r_frame.split("/")
            den_i = int(den)
            fps = round(int(num) / den_i, 3) if den_i else None
        except Exception:
            pass

    return {
        "duration": duration,
        "width": int(vs["width"]) if vs and vs.get("width") else None,
        "height": int(vs["height"]) if vs and vs.get("height") else None,
        "fps": fps,
        "has_audio": len(audio_streams) > 0,
        "codec_video": vs.get("codec_name") if vs else None,
        "codec_audio": aus.get("codec_name") if aus else None,
        "decodable": True,
        "ffprobe_skipped": False,
        "error": None,
    }
