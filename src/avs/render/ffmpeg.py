"""src/avs/render/ffmpeg.py — FFmpeg 粗剪渲染主控。

渲染策略：
1. 为每个 video clip 生成标准化段（contain/cover/placeholder）
2. concat 所有段生成无字幕 preview-clean.mp4
3. 混合音频（旁白 + BGM ducking）
4. burn SRT 生成 preview-with-captions.mp4
5. 幂等：若产物已存在且 force=False 跳过
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from avs.render.filters import scale_pad_filter, scale_crop_filter
from avs.render.layouts import choose_layout
from avs.timeline.models import Clip, Timeline

logger = logging.getLogger(__name__)

# 标准画布
CANVAS_W = 1080
CANVAS_H = 1920
FPS = 30

# 支持的视频扩展名
_VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".flv"}
# 支持的图片扩展名
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}


class RenderError(Exception):
    """渲染失败。"""


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


def _run(cmd: list[str], label: str = "", timeout: int = 300) -> subprocess.CompletedProcess:
    """执行命令，检查退出码；非零时抛出 RenderError。"""
    logger.debug("运行: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        msg = (result.stderr or result.stdout or "")[:500]
        raise RenderError(f"{label or cmd[0]} 失败 (exit {result.returncode}): {msg}")
    return result


def _probe_media(path: Path) -> dict[str, Any]:
    """轻量 ffprobe，仅获取宽高时长。"""
    if not ffprobe_available():
        return {}
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", str(path)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return {}
        data = json.loads(r.stdout)
        vs = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
        return {
            "width": int(vs["width"]) if vs and vs.get("width") else None,
            "height": int(vs["height"]) if vs and vs.get("height") else None,
        }
    except Exception:
        return {}


def _is_image(path: Path) -> bool:
    return path.suffix.lower() in _IMAGE_EXTS


def _is_video(path: Path) -> bool:
    return path.suffix.lower() in _VIDEO_EXTS


def _render_segment(
    clip: Clip,
    ep_dir: Path,
    work_dir: Path,
    idx: int,
) -> Path:
    """将单个 clip 渲染成标准化 .ts 段（1080×1920, 30fps, H.264）。

    返回输出 .ts 路径。
    """
    out_path = work_dir / f"seg_{idx:04d}.ts"

    # 确定素材路径
    asset_path: Path | None = None
    if clip.asset_ref:
        candidate = ep_dir / clip.asset_ref
        if candidate.exists():
            asset_path = candidate

    dur = clip.duration
    in_pt = clip.in_point if clip.in_point is not None else 0.0

    # ── 占位卡（黑底白字）────────────────────────────────────────────────
    if asset_path is None:
        text = clip.text or "[缺失素材]"
        vf = placeholder_drawtext_filter(text, CANVAS_W, CANVAS_H, FPS)
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=black:s={CANVAS_W}x{CANVAS_H}:r={FPS}:d={dur}",
            "-vf", f"drawtext=text='{_escape_drawtext(text)}':fontcolor=white:fontsize=36"
                   f":x=(w-text_w)/2:y=(h-text_h)/2",
            "-t", str(dur),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-an",
            "-f", "mpegts", str(out_path),
        ]
        _run(cmd, f"placeholder seg {idx}")
        return out_path

    # ── 图片 → 视频 ──────────────────────────────────────────────────────
    if _is_image(asset_path):
        vf = scale_pad_filter(CANVAS_W, CANVAS_H, FPS)
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(asset_path),
            "-vf", vf,
            "-t", str(dur),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-an",
            "-f", "mpegts", str(out_path),
        ]
        _run(cmd, f"image seg {idx}")
        return out_path

    # ── 视频片段 ─────────────────────────────────────────────────────────
    meta = _probe_media(asset_path)
    src_w = meta.get("width")
    src_h = meta.get("height")
    vf = choose_layout(clip.transform, src_w, src_h)

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(in_pt),
        "-i", str(asset_path),
        "-t", str(dur),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-an",
        "-f", "mpegts", str(out_path),
    ]
    _run(cmd, f"video seg {idx}")
    return out_path


def _escape_drawtext(text: str) -> str:
    """转义 FFmpeg drawtext 中的特殊字符。"""
    return (text
            .replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace(":", "\\:")
            .replace("[", "\\[")
            .replace("]", "\\]"))


def _concat_segments(seg_paths: list[Path], out_path: Path) -> None:
    """concat 所有 .ts 段到输出文件（仅视频轨）。"""
    if not seg_paths:
        raise RenderError("无可 concat 的视频段")

    # 使用 concat demuxer
    concat_list = out_path.parent / "concat_list.txt"
    lines = [f"file '{str(p).replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n" for p in seg_paths]
    concat_list.write_text("".join(lines), encoding="utf-8")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(out_path),
    ]
    _run(cmd, "concat segments")
    concat_list.unlink(missing_ok=True)


def _mix_audio_and_mux(
    video_path: Path,
    out_path: Path,
    total_duration: float,
    voice_path: Path | None,
    bgm_path: Path | None,
    voice_volume: float = 1.0,
    bgm_volume: float = 0.3,
) -> None:
    """将音频混合进视频；无音频时复制视频并生成静音轨。"""
    inputs = ["-i", str(video_path)]
    audio_count = 0
    voice_idx: int | None = None
    bgm_idx: int | None = None

    if voice_path and voice_path.exists():
        inputs += ["-i", str(voice_path)]
        audio_count += 1
        voice_idx = audio_count

    if bgm_path and bgm_path.exists():
        inputs += ["-i", str(bgm_path)]
        audio_count += 1
        bgm_idx = audio_count

    if audio_count == 0:
        # 无音频：生成静音轨
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
            "-shortest",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            str(out_path),
        ]
        _run(cmd, "mux silent audio")
        return

    if audio_count == 1:
        # 确定实际使用的音频流索引（voice_idx or bgm_idx，其中一个必为 int）
        if voice_idx is not None:
            vol = voice_volume
            audio_src_idx: int = voice_idx
        else:
            vol = bgm_volume
            audio_src_idx = bgm_idx  # type: ignore[assignment]
        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex",
            f"[{audio_src_idx}:a]volume={vol},atrim=duration={total_duration},apad[a]",
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            str(out_path),
        ]
        _run(cmd, "mux single audio")
        return

    # 双音轨：旁白 + BGM ducking（简化版：固定降低 BGM 音量）
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex",
        f"[{voice_idx}:a]volume={voice_volume},atrim=duration={total_duration}[v];"
        f"[{bgm_idx}:a]volume={bgm_volume},atrim=duration={total_duration}[b];"
        f"[v][b]amix=inputs=2:duration=first[a]",
        "-map", "0:v",
        "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(out_path),
    ]
    _run(cmd, "mux mixed audio")


def _burn_captions(
    input_video: Path,
    srt_path: Path,
    output_path: Path,
) -> None:
    """烧录 SRT 字幕到视频。"""
    if not srt_path.exists() or srt_path.stat().st_size == 0:
        # 无字幕：直接复制
        shutil.copy2(str(input_video), str(output_path))
        return

    # Windows 路径处理：先规范化为正斜杠，再转义驱动器号冒号
    srt_str = str(srt_path.resolve()).replace("\\", "/")
    # C:/path/... → C\:/path/... （FFmpeg subtitles filter 要求转义冒号）
    if len(srt_str) > 1 and srt_str[1] == ":":
        drive_colon_escaped = srt_str[0] + "\\:" + srt_str[2:]
    else:
        drive_colon_escaped = srt_str

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_video),
        "-vf", f"subtitles='{drive_colon_escaped}':force_style='FontSize=30,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=80'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        str(output_path),
    ]
    try:
        _run(cmd, "burn subtitles")
    except RenderError as exc:
        logger.warning("字幕烧录失败，复制无字幕版本: %s", exc)
        shutil.copy2(str(input_video), str(output_path))


def render_rough_cut(
    ep_dir: Path,
    timeline: Timeline,
    *,
    force: bool = False,
) -> dict[str, Path]:
    """执行完整粗剪渲染流程。

    返回：{"preview_clean": Path, "preview_with_captions": Path}
    """
    if not ffmpeg_available():
        raise RenderError("ffmpeg 未安装或不在 PATH 中")

    renders_dir = ep_dir / "renders"
    renders_dir.mkdir(parents=True, exist_ok=True)

    clean_out = renders_dir / "preview-clean.mp4"
    captions_out = renders_dir / "preview-with-captions.mp4"

    # 幂等检查
    if clean_out.exists() and captions_out.exists() and not force:
        logger.info("粗剪产物已存在，跳过渲染（use --force 重建）")
        return {"preview_clean": clean_out, "preview_with_captions": captions_out}

    # ── 阶段1：逐 clip 渲染标准化段 ────────────────────────────────────
    video_track = None
    for t in timeline.tracks:
        if t.kind == "video":
            video_track = t
            break

    if not video_track or not video_track.clips:
        raise RenderError("时间线中无 video 轨道或无 clips")

    with tempfile.TemporaryDirectory(prefix="avs_render_") as tmp_str:
        tmp_dir = Path(tmp_str)

        seg_paths: list[Path] = []
        for idx, clip in enumerate(video_track.clips):
            seg = _render_segment(clip, ep_dir, tmp_dir, idx)
            seg_paths.append(seg)

        # ── 阶段2：concat 所有段 → video_only.mp4 ──────────────────────
        video_only = tmp_dir / "video_only.mp4"
        _concat_segments(seg_paths, video_only)

        # ── 阶段3：查找音频素材 ─────────────────────────────────────────
        voice_path: Path | None = None
        bgm_path: Path | None = None
        voice_volume = 1.0
        bgm_volume = 0.3

        for t in timeline.tracks:
            if t.kind == "audio" and t.clips:
                clip = t.clips[0]
                if clip.asset_ref:
                    p = ep_dir / clip.asset_ref
                    style = clip.style or {}
                    role = style.get("role", "")
                    if role == "voice" or "voice" in t.track_id:
                        voice_path = p
                        voice_volume = float(style.get("volume", 1.0))
                    elif role == "bgm" or "music" in t.track_id:
                        bgm_path = p
                        bgm_volume = float(style.get("volume", 0.3))

        total_dur = timeline.total_duration or timeline.compute_duration()

        # ── 阶段4：混音 → preview_clean.mp4（无字幕）──────────────────
        _mix_audio_and_mux(
            video_only, clean_out, total_dur,
            voice_path=voice_path, bgm_path=bgm_path,
            voice_volume=voice_volume, bgm_volume=bgm_volume,
        )
        logger.info("preview-clean.mp4 已生成: %s", clean_out)

        # ── 阶段5：字幕烧录 → preview_with_captions.mp4 ────────────────
        srt_path = ep_dir / "work" / "captions.srt"
        if not srt_path.exists():
            srt_path = ep_dir / "delivery" / "captions.srt"

        _burn_captions(clean_out, srt_path, captions_out)
        logger.info("preview-with-captions.mp4 已生成: %s", captions_out)

    return {"preview_clean": clean_out, "preview_with_captions": captions_out}
