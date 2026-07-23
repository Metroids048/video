"""src/avs/timeline/models.py — 时间线数据模型。

与 schemas/timeline.schema.json 保持一致；不依赖 Pydantic，只用 dataclass
以减少外部依赖。所有路径为相对路径字符串（相对于 episode 根）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


@dataclass
class Canvas:
    width: int = 1080
    height: int = 1920
    fps: float = 30.0


@dataclass
class Clip:
    clip_id: str
    start: float               # 轨道起始秒
    duration: float            # 片段时长秒

    # 可选字段
    asset_ref: str | None = None     # 相对路径或 renderer 标识
    in_point: float | None = None    # 素材截取起点
    out_point: float | None = None   # 素材截取终点
    transform: dict[str, Any] | None = None  # 例如 {"layout": "contain"}
    text: str | None = None          # 文字内容（字幕/占位卡）
    style: dict[str, Any] | None = None      # 样式参数

    @property
    def end(self) -> float:
        return self.start + self.duration

    def to_dict(self) -> dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "start": self.start,
            "duration": self.duration,
            "asset_ref": self.asset_ref,
            "in_point": self.in_point,
            "out_point": self.out_point,
            "transform": self.transform,
            "text": self.text,
            "style": self.style,
        }


@dataclass
class Track:
    track_id: str
    kind: str          # "video" | "audio" | "caption" | "graphic"
    clips: list[Clip] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "kind": self.kind,
            "clips": [c.to_dict() for c in self.clips],
        }


@dataclass
class Timeline:
    episode_id: str
    canvas: Canvas = field(default_factory=Canvas)
    tracks: list[Track] = field(default_factory=list)
    total_duration: float | None = None
    version: str = "1.0"

    def compute_duration(self) -> float:
        """从所有轨道 clip 计算总时长。"""
        max_end = 0.0
        for track in self.tracks:
            for clip in track.clips:
                max_end = max(max_end, clip.end)
        return round(max_end, 3)

    def get_track(self, kind: str) -> Track | None:
        for t in self.tracks:
            if t.kind == kind:
                return t
        return None

    def to_dict(self) -> dict[str, Any]:
        dur = self.total_duration if self.total_duration is not None else self.compute_duration()
        return {
            "episode_id": self.episode_id,
            "version": self.version,
            "canvas": {"width": self.canvas.width, "height": self.canvas.height, "fps": self.canvas.fps},
            "total_duration": dur,
            "tracks": [t.to_dict() for t in self.tracks],
            "generated_at": _now_iso(),
        }

    def save(self, path: Path) -> None:
        """原子写入 timeline.json。"""
        tmp = path.with_suffix(".json.tmp")
        try:
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(self.to_dict(), fh, ensure_ascii=False, indent=2)
            tmp.replace(path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    @classmethod
    def load(cls, path: Path) -> "Timeline":
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        canvas = Canvas(**data["canvas"])
        tracks = []
        for td in data.get("tracks", []):
            clips = [Clip(**{
                k: v for k, v in cd.items()
                if k in ("clip_id","start","duration","asset_ref","in_point","out_point","transform","text","style")
            }) for cd in td.get("clips", [])]
            tracks.append(Track(track_id=td["track_id"], kind=td["kind"], clips=clips))
        return cls(
            episode_id=data["episode_id"],
            canvas=canvas,
            tracks=tracks,
            total_duration=data.get("total_duration"),
            version=data.get("version", "1.0"),
        )
