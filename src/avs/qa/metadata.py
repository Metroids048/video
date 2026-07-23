"""FFprobe metadata extraction for QA."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def probe_media(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size == 0:
        return {"error": "文件不存在或为空"}
    if not shutil.which("ffprobe"):
        return {"error": "ffprobe 不可用"}
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        return {"error": f"ffprobe 失败: {(result.stderr or '')[-300:]}"}
    try:
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        video = next((item for item in streams if item.get("codec_type") == "video"), None)
        audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
        if not video:
            return {"error": "无视频流"}
        rate = video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1"
        numerator, denominator = (int(value) for value in rate.split("/"))
        return {
            "width": int(video.get("width", 0)),
            "height": int(video.get("height", 0)),
            "fps": numerator / denominator if denominator else 0.0,
            "duration": float(data.get("format", {}).get("duration") or 0),
            "video_codec": video.get("codec_name"),
            "audio_codec": audio.get("codec_name") if audio else None,
            "has_audio": audio is not None,
            "size_bytes": path.stat().st_size,
        }
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        return {"error": f"ffprobe 输出解析失败: {exc}"}
