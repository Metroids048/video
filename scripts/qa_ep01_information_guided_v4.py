"""Deterministic + reviewer-gated QA for EP01 information-guided V4.

Freeze detection is evidence discovery, never an automatic quality verdict.
A publishable PASS requires deterministic media checks plus explicit reviewer
judgments for continuity, mobile readability, subtitles, semantic sync/content.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

BLOCKING_STATUS_NAMES = (
    "TECHNICAL", "VISUAL_CONTINUITY", "MOBILE_READABILITY", "SUBTITLE",
    "AUDIO", "AUDIO_VISUAL_SEMANTIC_SYNC", "CONTENT",
)


def publishable(statuses: dict[str, str]) -> str:
    return "PASS" if all(statuses.get(k) == "PASS" for k in BLOCKING_STATUS_NAMES) else "FAIL"


def _stream(probe: dict, kind: str) -> dict:
    return next((s for s in probe.get("streams", []) if s.get("codec_type") == kind), {})


def _fps(value: str) -> float:
    a, b = (value or "0/1").split("/", 1)
    return float(a) / float(b)


def evaluate_technical(probe: dict, decode_error_bytes: int, black_intervals: list[dict]) -> dict:
    v, a = _stream(probe, "video"), _stream(probe, "audio")
    failures = []
    if v.get("codec_name") != "h264": failures.append("video_codec_not_h264")
    if v.get("profile") != "High": failures.append("video_profile_not_high")
    if (v.get("width"), v.get("height")) != (1080, 1920): failures.append("video_resolution_not_1080x1920")
    if abs(_fps(v.get("r_frame_rate", "0/1")) - 30.0) > 0.01: failures.append("video_fps_not_30")
    if v.get("pix_fmt") != "yuv420p": failures.append("video_pix_fmt_not_yuv420p")
    if int(v.get("bit_rate") or 0) < 6_000_000: failures.append("video_bitrate_below_6mbps")
    if a.get("codec_name") != "aac": failures.append("audio_codec_not_aac")
    if int(a.get("sample_rate") or 0) != 48000: failures.append("audio_sample_rate_not_48khz")
    if int(a.get("channels") or 0) != 2: failures.append("audio_not_stereo")
    if decode_error_bytes: failures.append("decode_errors_present")
    if black_intervals: failures.append("black_frame_interval_present")
    v_start, a_start = float(v.get("start_time") or 0), float(a.get("start_time") or 0)
    v_dur = float(v.get("duration") or probe.get("format", {}).get("duration") or 0)
    a_dur = float(a.get("duration") or 0)
    start_delta_ms = abs(v_start - a_start) * 1000
    end_delta_ms = abs((v_start + v_dur) - (a_start + a_dur)) * 1000
    if start_delta_ms > 20: failures.append("av_start_delta_over_20ms")
    if end_delta_ms > 50: failures.append("av_end_delta_over_50ms")
    return {"status": "PASS" if not failures else "FAIL", "failures": failures,
            "av_start_delta_ms": round(start_delta_ms, 3), "av_end_delta_ms": round(end_delta_ms, 3),
            "video_bitrate_bps": int(v.get("bit_rate") or 0), "video_duration_s": v_dur, "audio_duration_s": a_dur}


def evaluate_audio(metrics: dict) -> dict:
    i, tp, lra = float(metrics["input_i"]), float(metrics["input_tp"]), float(metrics["input_lra"])
    failures = []
    if not (-16.5 <= i <= -13.5): failures.append("integrated_loudness_outside_target")
    if tp > -1.0: failures.append("true_peak_above_minus_1dbtp")
    return {"status": "PASS" if not failures else "FAIL", "failures": failures,
            "integrated_lufs": i, "true_peak_dbtp": tp, "lra_lu": lra}


def evaluate_visual_review(*, freezes: list[dict], manual_continuity_pass: bool,
                           mobile_readability_pass: bool, notes: list[str]) -> dict:
    return {"VISUAL_CONTINUITY": "PASS" if manual_continuity_pass else "FAIL",
            "MOBILE_READABILITY": "PASS" if mobile_readability_pass else "FAIL",
            "freeze_policy": "diagnostic_only", "freeze_findings": freezes, "review_notes": notes}


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def parse_freeze_black(text: str, total_duration: float) -> tuple[list[dict], list[dict]]:
    freezes, pending = [], None
    for line in text.splitlines():
        m = re.search(r"freeze_start: ([0-9.]+)", line)
        if m:
            pending = float(m.group(1)); continue
        m = re.search(r"freeze_end: ([0-9.]+)", line)
        if m and pending is not None:
            end = float(m.group(1)); freezes.append({"start": pending, "end": end, "duration": round(end-pending, 3)}); pending = None
    if pending is not None:
        freezes.append({"start": pending, "end": total_duration, "duration": round(total_duration-pending, 3)})
    blacks = [{"start": float(m.group(1)), "end": float(m.group(2)), "duration": float(m.group(3))}
              for m in re.finditer(r"black_start:([0-9.]+) black_end:([0-9.]+) black_duration:([0-9.]+)", text)]
    return freezes, blacks


def parse_loudnorm(text: str) -> dict:
    matches = list(re.finditer(r'\{\s*"input_i".*?\}', text, re.S))
    if not matches: raise ValueError("loudnorm metrics missing")
    return json.loads(matches[-1].group(0))


def parse_scene_times(text: str) -> list[float]:
    return [round(float(x), 3) for x in re.findall(r"pts_time:([0-9.]+)", text)]


def parse_silences(text: str) -> list[dict]:
    starts, result = [], []
    for line in text.splitlines():
        m = re.search(r"silence_start: ([0-9.]+)", line)
        if m: starts.append(float(m.group(1)))
        m = re.search(r"silence_end: ([0-9.]+) \| silence_duration: ([0-9.]+)", line)
        if m and starts:
            result.append({"start": starts.pop(0), "end": float(m.group(1)), "duration": float(m.group(2))})
    return result


def run_qa(video: Path, out_dir: Path, manual_review: dict) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    probe = json.loads(run(["ffprobe","-v","error","-show_format","-show_streams","-of","json",str(video)]).stdout)
    total = float(probe.get("format", {}).get("duration") or 0)
    decode = run(["ffmpeg","-hide_banner","-v","error","-i",str(video),"-f","null","-"])
    fb = run(["ffmpeg","-hide_banner","-i",str(video),"-vf","freezedetect=n=-45dB:d=2.5,blackdetect=d=0.2:pix_th=0.10","-an","-f","null","-"])
    freezes, blacks = parse_freeze_black(fb.stderr, total)
    scenes_p = run(["ffmpeg","-hide_banner","-i",str(video),"-vf","select='gt(scene,0.18)',showinfo","-an","-f","null","-"])
    loud = run(["ffmpeg","-hide_banner","-i",str(video),"-af","loudnorm=I=-16:TP=-1.0:LRA=7:print_format=json","-f","null","-"])
    silence = run(["ffmpeg","-hide_banner","-i",str(video),"-af","silencedetect=noise=-35dB:d=0.20","-f","null","-"])
    technical = evaluate_technical(probe, len(decode.stderr.encode()), blacks)
    audio = evaluate_audio(parse_loudnorm(loud.stderr))
    visual = evaluate_visual_review(freezes=freezes,
        manual_continuity_pass=bool(manual_review.get("visual_continuity_pass")),
        mobile_readability_pass=bool(manual_review.get("mobile_readability_pass")), notes=list(manual_review.get("notes", [])))
    statuses = {"TECHNICAL": technical["status"], "VISUAL_CONTINUITY": visual["VISUAL_CONTINUITY"],
        "MOBILE_READABILITY": visual["MOBILE_READABILITY"], "SUBTITLE": "PASS" if manual_review.get("subtitle_pass") else "FAIL",
        "AUDIO": audio["status"], "AUDIO_VISUAL_SEMANTIC_SYNC": "PASS" if manual_review.get("semantic_sync_pass") else "FAIL",
        "CONTENT": "PASS" if manual_review.get("content_pass") else "FAIL"}
    statuses["PUBLISHABLE"] = publishable(statuses)
    evidence = {"video": str(video), "probe": probe, "technical": technical, "audio": audio,
        "freeze_policy": "diagnostic_only", "freezes": freezes, "black_intervals": blacks,
        "scene_change_times_s": parse_scene_times(scenes_p.stderr), "silence_intervals": parse_silences(silence.stderr),
        "manual_review": manual_review, "statuses": statuses}
    (out_dir / "EP01_V4_检测证据.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "EP01_V4_技术验收.json").write_text(json.dumps({"statuses": statuses, "technical": technical,
        "audio": audio, "black_intervals": blacks, "freeze_policy": "diagnostic_only"}, ensure_ascii=False, indent=2), encoding="utf-8")
    return evidence


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--manual-review", type=Path, required=True)
    ns = ap.parse_args()
    result = run_qa(ns.video, ns.out_dir, json.loads(ns.manual_review.read_text(encoding="utf-8")))
    print(json.dumps(result["statuses"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
