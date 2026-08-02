"""cut.quality — export verification for rendered video files."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def _parse_fps(value: str) -> float:
    if not value:
        return 0.0
    if "/" in value:
        num, den = value.split("/", 1)
        try:
            return float(num) / float(den)
        except (TypeError, ValueError, ZeroDivisionError):
            return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def probe_file(path: str) -> Dict[str, Any]:
    """Run ffprobe and return parsed JSON. Returns an error dict if unavailable."""
    if not Path(path).exists():
        return {"error": f"file not found: {path}"}
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return {"error": "ffprobe not installed"}
    except subprocess.TimeoutExpired:
        return {"error": "ffprobe timed out"}
    if result.returncode != 0:
        return {"error": result.stderr[-1000:]}
    return json.loads(result.stdout or "{}")


def analyze_export(
    path: str,
    expected_duration_us: Optional[int] = None,
    ffprobe_json: Optional[Dict[str, Any]] = None,
    min_video_bitrate: int = 1_000_000,
    duration_tolerance_us: int = 1_000_000,
) -> Dict[str, Any]:
    """Validate an exported file and return a production QA report."""
    data = ffprobe_json if ffprobe_json is not None else probe_file(path)
    findings: List[Dict[str, str]] = []
    if data.get("error"):
        return {
            "success": False,
            "path": path,
            "findings": [{"severity": "error", "code": "probe_failed", "message": data["error"]}],
        }

    fmt = data.get("format", {})
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})

    duration_us = int(float(fmt.get("duration") or 0) * 1_000_000)
    bitrate = int(float(fmt.get("bit_rate") or 0))
    fps = _parse_fps(video.get("r_frame_rate", ""))

    if expected_duration_us is not None and abs(duration_us - expected_duration_us) > duration_tolerance_us:
        findings.append({
            "severity": "error",
            "code": "duration_mismatch",
            "message": f"duration {duration_us}us differs from expected {expected_duration_us}us",
        })
    if not video:
        findings.append({"severity": "error", "code": "missing_video_stream", "message": "no video stream found"})
    if bitrate and bitrate < min_video_bitrate:
        findings.append({
            "severity": "warning",
            "code": "video_bitrate_low",
            "message": f"bitrate {bitrate} is below {min_video_bitrate}",
        })
    if video and (int(video.get("width", 0)) <= 0 or int(video.get("height", 0)) <= 0):
        findings.append({"severity": "error", "code": "invalid_resolution", "message": "video resolution is missing"})
    if video and fps <= 0:
        findings.append({"severity": "error", "code": "invalid_fps", "message": "frame rate is missing"})
    if not audio:
        findings.append({"severity": "warning", "code": "missing_audio_stream", "message": "no audio stream found"})

    return {
        "success": not any(item["severity"] == "error" for item in findings) and not any(
            item["severity"] == "warning" for item in findings
        ),
        "path": path,
        "exists": os.path.exists(path) if ffprobe_json is None else None,
        "duration_us": duration_us,
        "bitrate": bitrate,
        "video": {
            "width": int(video.get("width", 0)) if video else 0,
            "height": int(video.get("height", 0)) if video else 0,
            "fps": fps,
        },
        "audio": {
            "sample_rate": int(audio.get("sample_rate", 0)) if audio else 0,
            "channels": int(audio.get("channels", 0)) if audio else 0,
        },
        "findings": findings,
    }


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate an exported video file.")
    parser.add_argument("path")
    parser.add_argument("--expected-duration-us", type=int)
    parser.add_argument("--min-video-bitrate", type=int, default=1_000_000)
    args = parser.parse_args(argv)
    report = analyze_export(
        args.path,
        expected_duration_us=args.expected_duration_us,
        min_video_bitrate=args.min_video_bitrate,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
