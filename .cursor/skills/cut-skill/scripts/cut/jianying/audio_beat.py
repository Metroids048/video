"""cut.jianying.audio_beat — 音频节拍识别（简化版）。

用于卡点视频，识别音频中的节拍时间点，让视频片段切换对齐节拍。

简化实现：基于能量峰值检测，不依赖 librosa。
完整实现可选用 librosa 获得更准确的节拍。
"""
from __future__ import annotations

import os
import wave
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional


def detect_beats(audio_path, min_interval_us=500_000, sensitivity=1.5):
    """检测音频节拍时间点。"""
    try:
        return _detect_beats_librosa(audio_path, min_interval_us, sensitivity)
    except ImportError:
        pass
    return _detect_beats_energy(audio_path, min_interval_us, sensitivity)


def _detect_beats_librosa(audio_path, min_interval_us, sensitivity):
    import librosa
    import numpy as np

    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    beats_us = [int(t * 1_000_000) for t in beat_times]

    filtered = []
    last = -min_interval_us
    for b in beats_us:
        if b - last >= min_interval_us:
            filtered.append(b)
            last = b

    duration_us = int(len(y) / sr * 1_000_000)
    bpm_val = float(tempo) if not hasattr(tempo, '__getitem__') else float(tempo[0])

    return {"beats": filtered, "bpm": bpm_val, "duration_us": duration_us,
            "engine": "librosa", "total_beats": len(filtered)}


def _detect_beats_energy(audio_path, min_interval_us, sensitivity):
    if not _which("ffmpeg"):
        return {"beats": [], "bpm": 0, "duration_us": 0, "error": "ffmpeg 未安装", "engine": "energy"}

    with tempfile.TemporaryDirectory() as tmp:
        wav_path = os.path.join(tmp, "audio.wav")
        subprocess.run(
            ["ffmpeg", "-y", "-i", audio_path,
             "-ar", "8000", "-ac", "1", "-acodec", "pcm_s16le", wav_path],
            capture_output=True, timeout=60,
        )

        if not os.path.exists(wav_path):
            return {"beats": [], "bpm": 0, "duration_us": 0, "error": "ffmpeg 转码失败", "engine": "energy"}

        try:
            with wave.open(wav_path, "rb") as wf:
                sample_width = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                raw = wf.readframes(n_frames)
        except Exception as e:
            return {"beats": [], "bpm": 0, "duration_us": 0, "error": f"wav 读取失败: {e}", "engine": "energy"}

        if sample_width != 2:
            return {"beats": [], "bpm": 0, "duration_us": 0, "error": "仅支持 16-bit wav", "engine": "energy"}

        samples = struct.unpack(f"<{n_frames}h", raw)
        duration_us = int(n_frames / framerate * 1_000_000)

        window_size = int(framerate * 0.05)
        energies = []
        for i in range(0, len(samples) - window_size, window_size):
            window = samples[i:i+window_size]
            energy = sum(s**2 for s in window) / window_size
            energies.append((i, energy))

        if not energies:
            return {"beats": [], "bpm": 0, "duration_us": duration_us, "engine": "energy"}

        avg_energy = sum(e for _, e in energies) / len(energies)
        threshold = avg_energy * sensitivity

        beats_us = []
        for i, (sample_idx, energy) in enumerate(energies):
            if energy > threshold:
                prev_e = energies[i-1][1] if i > 0 else 0
                next_e = energies[i+1][1] if i+1 < len(energies) else 0
                if energy >= prev_e and energy >= next_e:
                    time_us = int(sample_idx / framerate * 1_000_000)
                    beats_us.append(time_us)

        filtered = []
        last = -min_interval_us
        for b in beats_us:
            if b - last >= min_interval_us:
                filtered.append(b)
                last = b

        if len(filtered) >= 2:
            intervals = [filtered[i+1] - filtered[i] for i in range(len(filtered)-1)]
            avg_interval = sum(intervals) / len(intervals)
            bpm = 60_000_000 / avg_interval if avg_interval > 0 else 0
        else:
            bpm = 0

        return {"beats": filtered, "bpm": round(bpm, 1), "duration_us": duration_us,
                "engine": "energy", "total_beats": len(filtered)}


def _which(cmd):
    import shutil
    return shutil.which(cmd)


def beat_sync_segments(draft, audio_segment_id, video_segment_ids, fade_us=100_000):
    """按音频节拍对齐视频片段切换。"""
    audio_raw = draft.get_segment_raw(audio_segment_id)
    if not audio_raw:
        raise KeyError(f"audio segment {audio_segment_id} 不存在")

    mat = draft.find_material(audio_raw.get("material_id", ""))
    if not mat or not mat.get("path"):
        return {"error": "找不到音频文件路径，无法检测节拍"}

    beat_result = detect_beats(mat["path"])
    beats = beat_result.get("beats", [])
    if not beats:
        return {"error": "未检测到节拍", "detail": beat_result}

    audio_tt = audio_raw.get("target_timerange", {})
    audio_start = int(audio_tt.get("start", 0))

    n_segs = len(video_segment_ids)
    if n_segs < 2:
        return {"error": "至少需要 2 个视频 segment"}

    switch_points = [audio_start] + beats[:n_segs-1]
    switch_points.append(audio_start + int(audio_tt.get("duration", 0)))

    from .segments import trim_segment
    from .effects import add_keyframe

    for i, sid in enumerate(video_segment_ids):
        seg_raw = draft.get_segment_raw(sid)
        if not seg_raw:
            continue
        new_start = switch_points[i]
        new_end = switch_points[i+1]
        try:
            track = draft.find_track_by_segment(sid)
            if track:
                seg_obj = track.find_segment(sid)
                if seg_obj:
                    trim_segment(draft, seg_obj, new_start_us=new_start, new_end_us=new_end)
        except Exception:
            pass

        add_keyframe(draft, sid, new_start, 0.0, field="alpha")
        add_keyframe(draft, sid, new_start + fade_us, 1.0, field="alpha")
        add_keyframe(draft, sid, new_end - fade_us, 1.0, field="alpha")
        add_keyframe(draft, sid, new_end, 0.0, field="alpha")

    return {"synced_segments": n_segs, "beats_used": len(beats[:n_segs-1]),
            "bpm": beat_result.get("bpm", 0), "engine": beat_result.get("engine")}
