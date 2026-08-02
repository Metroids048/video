"""cut.jianying.materials — 素材导入管理。

向剪映 draft 添加视频/音频/图片素材，并返回 material_id。
注意：添加 material 后还需要 add_segment 把它放到时间轴上才算真正使用。

剪映素材字段（v5.x video material 关键字段）：
- id: 素材唯一 ID
- path: 本地文件绝对路径
- duration: 素材时长（微秒）
- width / height: 分辨率
- fps: 帧率
- type: "video" / "audio" / "image"
- 视频还有: rotation, scale, has_audio, fps, md5 等
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any

from .draft import Draft, _new_id


# ---------------------------------------------------------------------------
# 媒体文件信息探测
# ---------------------------------------------------------------------------

def _probe_media(path: str) -> Dict[str, Any]:
    """探测媒体文件信息。

    优先用 ffmpeg（如果安装），否则用基本文件信息。
    返回 {duration, width, height, fps, has_audio, type, size_bytes}。
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"媒体文件不存在: {path}")

    info: Dict[str, Any] = {
        "path": str(p.absolute()),
        "size_bytes": p.stat().st_size,
        "duration": 0,
        "width": 0,
        "height": 0,
        "fps": 30.0,
        "has_audio": False,
        "type": "unknown",
    }

    ext = p.suffix.lower()
    if ext in (".mp4", ".mov", ".mkv", ".avi", ".flv", ".webm", ".m4v"):
        info["type"] = "video"
    elif ext in (".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg", ".wma"):
        info["type"] = "audio"
    elif ext in (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif", ".tiff"):
        info["type"] = "image"

    # 尝试用 ffprobe
    try:
        import subprocess
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", str(p)],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0:
            import json
            data = json.loads(out.stdout)
            fmt = data.get("format", {})
            streams = data.get("streams", [])
            duration = float(fmt.get("duration", 0))
            info["duration"] = int(duration * 1_000_000)
            for s in streams:
                if s.get("codec_type") == "video":
                    info["width"] = int(s.get("width", 0))
                    info["height"] = int(s.get("height", 0))
                    fps_str = s.get("r_frame_rate", "30/1")
                    try:
                        num, den = fps_str.split("/")
                        info["fps"] = float(num) / float(den) if float(den) else 30.0
                    except Exception:
                        info["fps"] = 30.0
                    info["type"] = "video"
                elif s.get("codec_type") == "audio":
                    info["has_audio"] = True
                    if info["type"] == "unknown":
                        info["type"] = "audio"
    except FileNotFoundError:
        # ffprobe 未安装，用最小信息
        pass
    except Exception:
        pass

    return info


# ---------------------------------------------------------------------------
# 导入素材
# ---------------------------------------------------------------------------

def import_video(draft: Draft, path: str,
                 alias: Optional[str] = None) -> str:
    """导入视频素材。返回 material_id。

    需要 ffmpeg/ffprobe 探测元数据（如未安装，时长/分辨率会为 0，
    剪映打开后仍能自动识别，但建议安装 ffmpeg）。
    """
    info = _probe_media(path)
    if info["type"] not in ("video",):
        raise ValueError(f"不是视频文件: {path}")

    mat_id = _new_id()
    material = {
        "id": mat_id,
        "type": "video",
        "path": info["path"],
        "duration": info["duration"],
        "width": info["width"],
        "height": info["height"],
        "fps": info["fps"],
        "has_audio": info["has_audio"],
        "material_name": alias or Path(path).stem,
        "local_id": "",
        "local_material_id": mat_id,
        "is_proxy": False,
        "is_copyright": False,
        "is_ai_generate": False,
        "md5": "",
        "object_id": "",
        "extra_material_id": "",
        "stable_material_id": mat_id,
        "team_id": "",
        "type_source": 0,
        "vfx_type": 0,
        "is_text_edit": False,
        "mask_info": {"mask_id": "", "mask_name": "", "mask_path": ""},
        "is_placeholder": False,
        "placeholder_id": "",
        "fursuer_effect": [],
        "source_platform": 0,
        "request_id": "",
        "import_time": 0,
        "category_id": "",
        "category_name": "",
        "intensifies_audio_path": "",
        "intensifies_path": "",
        "is_valid": True,
        "is_gif": False,
        "is_capture": False,
        "is_template": False,
        "is_pano": False,
        "is_recycle": False,
        "is_selected": False,
    }
    draft.add_material("video", material)
    return mat_id


def import_audio(draft: Draft, path: str,
                 alias: Optional[str] = None) -> str:
    """导入音频素材。返回 material_id。"""
    info = _probe_media(path)
    if info["type"] != "audio":
        raise ValueError(f"不是音频文件: {path}")

    mat_id = _new_id()
    material = {
        "id": mat_id,
        "type": "audio",
        "path": info["path"],
        "duration": info["duration"],
        "material_name": alias or Path(path).stem,
        "name": alias or Path(path).name,
        "local_id": "",
        "local_material_id": mat_id,
        "md5": "",
        "object_id": "",
        "extra_material_id": "",
        "stable_material_id": mat_id,
        "source_platform": 0,
        "request_id": "",
        "team_id": "",
        "is_valid": True,
        "is_copyright": False,
        "is_ai_generate": False,
        "category_id": "",
        "category_name": "",
        "intensifies_audio_path": "",
        "import_time": 0,
        "app_id": "",
        "business_id": 0,
        "fursuer_effect": [],
    }
    draft.add_material("audio", material)
    return mat_id


def import_image(draft: Draft, path: str,
                 alias: Optional[str] = None,
                 duration_us: int = 5_000_000) -> str:
    """导入图片素材。返回 material_id。

    图片没有时长，duration_us 默认 5 秒（仅用于添加到时间轴时）。
    """
    info = _probe_media(path)
    if info["type"] != "image":
        raise ValueError(f"不是图片文件: {path}")

    mat_id = _new_id()
    material = {
        "id": mat_id,
        "type": "photo",
        "path": info["path"],
        "duration": duration_us,
        "width": info["width"],
        "height": info["height"],
        "material_name": alias or Path(path).stem,
        "local_id": "",
        "local_material_id": mat_id,
        "md5": "",
        "object_id": "",
        "extra_material_id": "",
        "stable_material_id": mat_id,
        "is_copyright": False,
        "is_ai_generate": False,
        "is_recycle": False,
        "source_platform": 0,
        "request_id": "",
        "team_id": "",
        "fursuer_effect": [],
        "category_id": "",
        "category_name": "",
        "import_time": 0,
        "is_valid": True,
    }
    # 注意剪映把图片放在 videos 数组里，type=photo
    draft.add_material("video", material)
    return mat_id


# ---------------------------------------------------------------------------
# 把素材放到时间轴
# ---------------------------------------------------------------------------

def add_video_segment(draft: Draft, material_id: str,
                      track_id: Optional[str] = None,
                      start_us: int = 0,
                      source_in_us: int = 0,
                      duration_us: Optional[int] = None,
                      ) -> str:
    """把视频/图片素材作为一个 segment 加到指定视频轨道。

    - track_id: None 时自动用第一条 video track，没有则创建
    - start_us: 时间轴起点
    - source_in_us: 素材内部入点（默认 0）
    - duration_us: 片段时长，None 时用素材全时长
    """
    mat = draft.find_material(material_id)
    if not mat:
        raise KeyError(f"material {material_id} 不存在")

    if track_id is None:
        vts = draft.video_tracks
        if vts:
            track_id = vts[0].id
        else:
            track_id = draft.add_track("video")

    if duration_us is None:
        duration_us = int(mat.get("duration", 5_000_000))

    seg = {
        "id": _new_id(),
        "material_id": material_id,
        "source_timerange": {"start": source_in_us, "duration": duration_us},
        "target_timerange": {"start": start_us, "duration": duration_us},
        "source_in_speed": 1.0,
        "speed": 1.0,
        "volume": 1.0,
        "is_placeholder": False,
        "responsive_layout": {"enable": False, "horizontal_pos_layout": 0, "vertical_pos_layout": 0, "width_layout": 0, "height_layout": 0, "target_follow": 0},
        "extra_material_refs": [],
        "common_keyframes": [],
        "material_animations": [],
        "enabled": True,
        "render_index": 0,
        "clip": {"alpha": 1.0, "flip": {"horizontal": False, "vertical": False}, "rotation": 0, "scale": {"x": 1.0, "y": 1.0}, "transform": {"x": 0, "y": 0}},
        "fursuer_effect": [],
        "reverse": False,
        "track_id": track_id,
        "visible": True,
        "collapsible": False,
        "hole_info": {"holes": []},
        "is_tone_adjust": False,
        "source": 0,
        "stage_width": 0,
        "stage_height": 0,
    }
    seg_id = draft.add_segment_raw(track_id, seg)
    draft.extend_duration()
    return seg_id


def add_audio_segment(draft: Draft, material_id: str,
                      track_id: Optional[str] = None,
                      start_us: int = 0,
                      source_in_us: int = 0,
                      duration_us: Optional[int] = None,
                      volume: float = 1.0) -> str:
    """把音频素材作为 segment 加到指定音频轨道。"""
    mat = draft.find_material(material_id)
    if not mat:
        raise KeyError(f"material {material_id} 不存在")

    if track_id is None:
        ats = draft.audio_tracks
        if ats:
            track_id = ats[0].id
        else:
            track_id = draft.add_track("audio")

    if duration_us is None:
        duration_us = int(mat.get("duration", 0))

    seg = {
        "id": _new_id(),
        "material_id": material_id,
        "source_timerange": {"start": source_in_us, "duration": duration_us},
        "target_timerange": {"start": start_us, "duration": duration_us},
        "source_in_speed": 1.0,
        "speed": 1.0,
        "volume": volume,
        "common_keyframes": [],
        "enabled": True,
        "render_index": 0,
        "track_id": track_id,
        "visible": True,
        "is_placeholder": False,
        "extra_material_refs": [],
        "source": 0,
        "fursuer_effect": [],
    }
    seg_id = draft.add_segment_raw(track_id, seg)
    draft.extend_duration()
    return seg_id
