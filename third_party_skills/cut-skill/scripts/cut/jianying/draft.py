"""cut.jianying.draft — 剪映 draft_content.json 解析与编辑核心。

剪映的工程文件是 JSON，位于 <drafts_dir>/<project_name>/draft_content.json。
本模块提供 Draft 类，封装：
- 打开/保存/备份
- 解析三层结构：materials → tracks → segments
- 增删改查的便捷方法
- 写回前自动校验 JSON 合法性

修改 draft 后，剪映需要重新打开项目才能看到效果（或在剪映中按 Ctrl+Z 重做一次
触发重载）。本模块不直接控制剪映 UI。

draft schema 关键字段（v5.x）：
- duration: 项目总时长（微秒）
- canvas_config: 画布尺寸
- materials: 素材池，子字段 videos/audios/images/stickers/texts/effects/audio_effects
- tracks: 轨道数组，每个 track 有 type (video/audio/text/sticker/effect) 和 segments
- id: 全局唯一 ID
- 创建时间、版本号等元数据
"""
from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterator, Union

from .. import platform as P


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------

class DraftError(Exception):
    """draft 操作通用异常。"""


class UnsupportedSchemaError(DraftError):
    """不支持的 draft schema 版本。"""


class SegmentNotFoundError(DraftError):
    pass


class TrackNotFoundError(DraftError):
    pass


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _new_id(prefix: str = "") -> str:
    """生成剪映风格的 ID。剪映用 UUID 去掉横线 + 前缀。"""
    return prefix + uuid.uuid4().hex


def _us(ms_or_s: Union[int, float, str], unit: str = "us") -> int:
    """把任意时间格式转微秒。

    支持：
    - int/float: 默认按 unit ("us"/"ms"/"s")
    - str:
        - 带后缀 "3000us" / "3000ms" / "3s" → 按后缀
        - "HH:MM:SS.mmm" / "MM:SS.mmm" → 时分秒格式
        - 裸数字字符串 "3000000" → 按 unit（默认 us，与 CLI 一致）
    """
    if isinstance(ms_or_s, str):
        s = ms_or_s.strip()
        # 带后缀
        if s.endswith("us"):
            return int(float(s[:-2]))
        if s.endswith("ms"):
            return int(float(s[:-2]) * 1000)
        if s.endswith("s"):
            return int(float(s[:-1]) * 1_000_000)
        # HH:MM:SS 格式
        parts = s.split(":")
        if len(parts) == 3:
            h, m, sec = parts
            return int(float(h) * 3_600_000_000 + float(m) * 60_000_000 + float(sec) * 1_000_000)
        elif len(parts) == 2:
            m, sec = parts
            return int(float(m) * 60_000_000 + float(sec) * 1_000_000)
        # 裸数字字符串：按 unit（默认 us）
        v = float(parts[0])
        if unit == "us":
            return int(v)
        if unit == "ms":
            return int(v * 1000)
        if unit == "s":
            return int(v * 1_000_000)
        raise ValueError(f"unknown unit {unit}")
    # int/float
    v = float(ms_or_s)
    if unit == "us":
        return int(v)
    if unit == "ms":
        return int(v * 1000)
    if unit == "s":
        return int(v * 1_000_000)
    raise ValueError(f"unknown unit {unit}")


def _hms(us: int) -> str:
    """微秒转 HH:MM:SS.mmm。"""
    if us is None:
        return "00:00:00.000"
    total_ms = us // 1000
    h = total_ms // 3_600_000
    m = (total_ms % 3_600_000) // 60_000
    s = (total_ms % 60_000) // 1000
    ms = total_ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

@dataclass
class TimeRange:
    """时间范围。剪映用 {duration, start} 表示，单位微秒。"""
    start: int
    duration: int

    @property
    def end(self) -> int:
        return self.start + self.duration

    def to_dict(self) -> Dict[str, int]:
        return {"start": self.start, "duration": self.duration}

    @classmethod
    def from_dict(cls, d: Optional[Dict]) -> "TimeRange":
        if not d:
            return cls(0, 0)
        return cls(start=int(d.get("start", 0)), duration=int(d.get("duration", 0)))


@dataclass
class Segment:
    """时间轴上的一个片段。"""
    id: str
    track_id: str
    material_id: str
    target_timerange: TimeRange        # 在时间轴上的位置
    source_timerange: TimeRange        # 在素材内部的范围
    source_in_speed: float = 1.0
    speed: float = 1.0
    volume: float = 1.0
    extra: Dict[str, Any] = field(default_factory=dict)  # 原始 JSON 保留

    @property
    def start_us(self) -> int:
        return self.target_timerange.start

    @property
    def duration_us(self) -> int:
        return self.target_timerange.duration

    @property
    def end_us(self) -> int:
        return self.target_timerange.end

    @property
    def source_start_us(self) -> int:
        return self.source_timerange.start

    @property
    def source_duration_us(self) -> int:
        return self.source_timerange.duration


@dataclass
class Track:
    """时间轴上的轨道。"""
    id: str
    type: str                          # video/audio/text/sticker/effect
    segments: List[Segment] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def iter_segments(self) -> Iterator[Segment]:
        return iter(self.segments)

    def find_segment(self, segment_id: str) -> Optional[Segment]:
        for s in self.segments:
            if s.id == segment_id:
                return s
        return None


@dataclass
class Material:
    """素材池中的一个素材。"""
    id: str
    type: str                          # video/audio/image/sticker/text/effect
    path: Optional[str] = None
    duration: int = 0
    width: int = 0
    height: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Draft 主体
# ---------------------------------------------------------------------------

class Draft:
    """剪映 draft 工程文件的高级封装。

    用法：
        draft = Draft.open(project_name="my_vlog")
        track = draft.video_tracks[0]
        seg = track.segments[0]
        # ... 修改 ...
        draft.save()
    """

    BACKUP_SUFFIX = ".bak"

    def __init__(self, project_dir: Path, content: Dict[str, Any]):
        self.project_dir = project_dir
        self.content = content
        self._modified = False
        self._backup_done = False

    # ----------------- 打开/保存 -----------------

    @classmethod
    def open(cls, project_name: Optional[str] = None,
             project_dir: Optional[Union[str, Path]] = None,
             app: str = "jianying") -> "Draft":
        """打开剪映项目。

        参数二选一：
        - project_name: 项目名，自动从 drafts_dir 查找
        - project_dir: 项目目录绝对路径
        """
        if project_dir:
            pdir = Path(project_dir)
        elif project_name:
            pdir = P.find_draft(project_name, app=app)
        else:
            raise ValueError("必须提供 project_name 或 project_dir")

        dc = pdir / "draft_content.json"
        if not dc.exists():
            raise DraftError(f"draft_content.json 不存在: {dc}")

        try:
            with open(dc, "r", encoding="utf-8") as f:
                content = json.load(f)
        except json.JSONDecodeError as e:
            raise DraftError(f"draft_content.json 解析失败: {e}") from e

        schema_v = content.get("draft_version") or content.get("version")
        # 已知支持 5.x schema。低版本给出警告但继续。
        if schema_v and schema_v.startswith("4."):
            # 不阻断，但记录
            pass

        return cls(pdir, content)

    def backup(self) -> Path:
        """备份当前 draft_content.json。"""
        dc = self.project_dir / "draft_content.json"
        # 用纳秒级时间戳 + 短 uuid 避免同秒覆盖
        ts = f"{int(time.time())}.{uuid.uuid4().hex[:6]}"
        bak = dc.with_suffix(dc.suffix + self.BACKUP_SUFFIX + "." + ts)
        if dc.exists():
            shutil.copy2(dc, bak)
        self._backup_done = True
        return bak

    def save(self, force_backup: bool = True) -> Path:
        """写回 draft_content.json。默认先备份。

        使用临时文件 + os.replace 原子替换，确保写入失败时不会损坏原文件。
        """
        import tempfile
        dc = self.project_dir / "draft_content.json"
        if force_backup and not self._backup_done and dc.exists():
            self.backup()

        # 写前校验 JSON 可序列化
        try:
            json.dumps(self.content, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            raise DraftError(f"content 不可序列化: {e}") from e

        # 原子写入：先写临时文件，再 os.replace 替换原文件
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=str(self.project_dir), suffix=".tmp", prefix=".draft_save_"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(self.content, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, dc)
        except Exception:
            # 写入失败，清理临时文件，原文件保持不变
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        self._modified = False
        self._backup_done = False
        return dc

    # ----------------- 元数据 -----------------

    @property
    def name(self) -> str:
        return self.project_dir.name

    @property
    def duration(self) -> int:
        return int(self.content.get("duration", 0))

    @property
    def duration_hms(self) -> str:
        return _hms(self.duration)

    @property
    def canvas(self) -> Dict[str, int]:
        cc = self.content.get("canvas_config", {})
        return {"width": int(cc.get("width", 1920)), "height": int(cc.get("height", 1080))}

    @property
    def schema_version(self) -> Optional[str]:
        return self.content.get("draft_version") or self.content.get("version")

    # ----------------- 素材池 -----------------

    @property
    def materials(self) -> Dict[str, Any]:
        return self.content.setdefault("materials", {})

    def list_materials(self, mtype: Optional[str] = None) -> List[Material]:
        """列出素材。mtype 可选 video/audio/image/sticker/text/effect。"""
        out: List[Material] = []
        m = self.materials
        buckets = {
            "video": "videos",
            "audio": "audios",
            "image": "images",
            "sticker": "stickers",
            "text": "texts",
            "effect": "effects",
        }
        keys = [buckets[mtype]] if mtype and mtype in buckets else list(buckets.values())
        for k in keys:
            for item in m.get(k, []):
                mid = item.get("id", "")
                # 推断 type
                t = next((kk for kk, vv in buckets.items() if vv == k), "unknown")
                out.append(Material(
                    id=mid,
                    type=t,
                    path=item.get("path") or item.get("material_name"),
                    duration=int(item.get("duration", 0)),
                    width=int(item.get("width", 0)),
                    height=int(item.get("height", 0)),
                    extra=item,
                ))
        return out

    def add_material(self, mtype: str, item: Dict[str, Any]) -> str:
        """向素材池添加素材，返回新 ID。"""
        buckets = {
            "video": "videos", "audio": "audios", "image": "images",
            "sticker": "stickers", "text": "texts", "effect": "effects",
            "audio_effect": "audio_effects",
        }
        key = buckets.get(mtype)
        if not key:
            raise DraftError(f"未知素材类型: {mtype}")
        bucket = self.materials.setdefault(key, [])
        if "id" not in item:
            item["id"] = _new_id()
        bucket.append(item)
        self._modified = True
        return item["id"]

    def find_material(self, material_id: str) -> Optional[Dict[str, Any]]:
        for k in ("videos", "audios", "images", "stickers", "texts", "effects", "audio_effects"):
            for item in self.materials.get(k, []):
                if item.get("id") == material_id:
                    return item
        return None

    # ----------------- 轨道 -----------------

    @property
    def tracks_raw(self) -> List[Dict[str, Any]]:
        return self.content.setdefault("tracks", [])

    @property
    def video_tracks(self) -> List[Track]:
        return [self._parse_track(t) for t in self.tracks_raw if t.get("type") == "video"]

    @property
    def audio_tracks(self) -> List[Track]:
        return [self._parse_track(t) for t in self.tracks_raw if t.get("type") == "audio"]

    @property
    def text_tracks(self) -> List[Track]:
        return [self._parse_track(t) for t in self.tracks_raw if t.get("type") == "text"]

    @property
    def sticker_tracks(self) -> List[Track]:
        return [self._parse_track(t) for t in self.tracks_raw if t.get("type") == "sticker"]

    @property
    def effect_tracks(self) -> List[Track]:
        return [self._parse_track(t) for t in self.tracks_raw if t.get("type") == "effect"]

    def all_tracks(self) -> List[Track]:
        return [self._parse_track(t) for t in self.tracks_raw]

    def get_track(self, track_id: str) -> Track:
        for t in self.all_tracks():
            if t.id == track_id:
                return t
        raise TrackNotFoundError(f"track {track_id} 不存在")

    def find_track_by_segment(self, segment_id: str) -> Optional[Track]:
        for t in self.all_tracks():
            if t.find_segment(segment_id):
                return t
        return None

    def _parse_track(self, raw: Dict[str, Any]) -> Track:
        segs: List[Segment] = []
        for s in raw.get("segments", []):
            tt = TimeRange.from_dict(s.get("target_timerange"))
            st = TimeRange.from_dict(s.get("source_timerange"))
            segs.append(Segment(
                id=s.get("id", ""),
                track_id=raw.get("id", ""),
                material_id=s.get("material_id", ""),
                target_timerange=tt,
                source_timerange=st,
                source_in_speed=float(s.get("source_in_speed", 1.0)),
                speed=float(s.get("speed", 1.0)),
                volume=float(s.get("volume", 1.0)),
                extra=s,
            ))
        return Track(
            id=raw.get("id", ""),
            type=raw.get("type", "video"),
            segments=segs,
            extra=raw,
        )

    def add_track(self, track_type: str, attrs: Optional[Dict] = None) -> str:
        """添加新轨道。track_type ∈ video/audio/text/sticker/effect。"""
        new_id = _new_id()
        track = {
            "id": new_id,
            "type": track_type,
            "segments": [],
            "attribute": attrs or 0,
            "flag": 0,
        }
        # video/audio 轨道有额外字段
        if track_type in ("video", "audio"):
            track["volume"] = 1.0
            track["visible"] = True
            track["enabled"] = True
        self.tracks_raw.append(track)
        self._modified = True
        return new_id

    # ----------------- 片段操作（通用增删） -----------------

    def add_segment_raw(self, track_id: str, segment: Dict[str, Any]) -> str:
        """直接向某 track 追加 segment 原始 dict。"""
        for t in self.tracks_raw:
            if t.get("id") == track_id:
                if "id" not in segment:
                    segment["id"] = _new_id()
                t.setdefault("segments", []).append(segment)
                self._modified = True
                return segment["id"]
        raise TrackNotFoundError(f"track {track_id} 不存在")

    def remove_segment(self, segment_id: str) -> bool:
        """删除片段。返回是否成功。"""
        for t in self.tracks_raw:
            segs = t.get("segments", [])
            for i, s in enumerate(segs):
                if s.get("id") == segment_id:
                    segs.pop(i)
                    self._modified = True
                    return True
        return False

    def get_segment_raw(self, segment_id: str) -> Optional[Dict[str, Any]]:
        for t in self.tracks_raw:
            for s in t.get("segments", []):
                if s.get("id") == segment_id:
                    return s
        return None

    # ----------------- 项目级操作 -----------------

    def extend_duration(self) -> None:
        """重算项目 duration，取所有 track 最末 segment 的 end 与当前 duration 的最大值。

        注意：本方法只增不减，适合 add/split/trim 后扩展项目时长。
        删除片段后请用 recalc_duration() 收缩。
        """
        max_end = 0
        for t in self.tracks_raw:
            for s in t.get("segments", []):
                tt = s.get("target_timerange", {})
                end = int(tt.get("start", 0)) + int(tt.get("duration", 0))
                if end > max_end:
                    max_end = end
        self.content["duration"] = max(self.duration, max_end)
        self._modified = True

    def recalc_duration(self) -> None:
        """重算项目 duration，严格等于所有 track 最末 segment 的 end。

        与 extend_duration 不同，本方法会收缩 duration（删除末尾片段后用）。
        """
        max_end = 0
        for t in self.tracks_raw:
            for s in t.get("segments", []):
                tt = s.get("target_timerange", {})
                end = int(tt.get("start", 0)) + int(tt.get("duration", 0))
                if end > max_end:
                    max_end = end
        self.content["duration"] = max_end
        self._modified = True

    # ----------------- 序列化 -----------------

    def to_summary(self) -> Dict[str, Any]:
        """返回适合给 agent 看的项目摘要。"""
        tracks = self.all_tracks()
        return {
            "name": self.name,
            "schema_version": self.schema_version,
            "duration_us": self.duration,
            "duration_hms": self.duration_hms,
            "canvas": self.canvas,
            "tracks": [
                {
                    "id": t.id,
                    "type": t.type,
                    "segments_count": len(t.segments),
                    "first_start_us": t.segments[0].start_us if t.segments else 0,
                    "last_end_us": t.segments[-1].end_us if t.segments else 0,
                }
                for t in tracks
            ],
            "materials": {
                k: len(self.materials.get(k, []))
                for k in ("videos", "audios", "images", "stickers", "texts", "effects", "audio_effects")
            },
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="cut.jianying.draft — 剪映 draft 解析")
    parser.add_argument("project", help="项目名或路径")
    parser.add_argument("--app", default="jianying", choices=["jianying", "capcut"])
    parser.add_argument("--summary", action="store_true", help="输出项目摘要")
    parser.add_argument("--materials", action="store_true", help="输出素材列表")
    parser.add_argument("--tracks", action="store_true", help="输出轨道结构")
    args = parser.parse_args()

    d = Draft.open(project_name=args.project, app=args.app)
    if args.summary or not (args.materials or args.tracks):
        print(json.dumps(d.to_summary(), indent=2, ensure_ascii=False))
    if args.materials:
        for m in d.list_materials():
            print(f"{m.type:8s} {m.id[:12]}  {m.path or ''}  {_hms(m.duration)}")
    if args.tracks:
        for t in d.all_tracks():
            print(f"\n[{t.type}] {t.id[:12]}  ({len(t.segments)} segments)")
            for s in t.segments:
                print(f"  {s.id[:12]}  material={s.material_id[:12]}  "
                      f"target={_hms(s.start_us)}~{_hms(s.end_us)}  "
                      f"source={_hms(s.source_start_us)}~{_hms(s.source_start_us + s.source_duration_us)}")
