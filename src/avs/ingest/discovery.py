"""src/avs/ingest/discovery.py — 扫描 input/ 目录，分类素材文件。"""
from __future__ import annotations

import mimetypes
from dataclasses import dataclass, field
from pathlib import Path

from avs.ingest.errors import PathTraversalError

# 扩展名 → kind 映射
_VIDEO_EXT = frozenset({".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".ts"})
_AUDIO_EXT = frozenset({".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg", ".opus"})
_IMAGE_EXT = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif"})
_TEXT_EXT  = frozenset({".txt", ".md", ".srt", ".json", ".yaml", ".yml", ".csv"})


@dataclass
class DiscoveredFile:
    """input/ 下的一个素材文件（未处理）。"""
    abs_path: Path            # 绝对路径（只读原文件）
    rel_path: str             # 相对于 episode_dir 的路径（用于 manifest）
    kind: str                 # video | audio | image | text | link | unknown
    mime_type: str
    size_bytes: int


def classify_kind(path: Path) -> tuple[str, str]:
    """根据文件名/扩展名返回 (kind, mime_type)。"""
    name = path.name.lower()
    suffix = path.suffix.lower()

    # links.txt 特殊处理
    if name == "links.txt":
        return "link", "text/plain"

    if suffix in _VIDEO_EXT:
        mime = mimetypes.guess_type(path.name)[0] or "video/mp4"
        return "video", mime
    if suffix in _AUDIO_EXT:
        mime = mimetypes.guess_type(path.name)[0] or "audio/mpeg"
        return "audio", mime
    if suffix in _IMAGE_EXT:
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        return "image", mime
    if suffix in _TEXT_EXT:
        return "text", "text/plain"

    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return "unknown", mime


def discover_inputs(episode_dir: Path) -> list[DiscoveredFile]:
    """递归扫描 episode_dir/input/ 下所有非隐藏文件。

    路径穿越防护：所有文件的绝对路径必须在 input_dir 内。
    跳过 .gitkeep 等占位文件。
    """
    input_dir = (episode_dir / "input").resolve()
    if not input_dir.exists():
        return []

    ep_resolved = episode_dir.resolve()
    found: list[DiscoveredFile] = []

    for file in sorted(input_dir.rglob("*")):
        if not file.is_file():
            continue
        if file.name.startswith("."):
            continue
        if file.name == ".gitkeep" or file.suffix == ".gitkeep":
            continue

        abs_path = file.resolve()

        # 路径穿越检测
        try:
            abs_path.relative_to(input_dir)
        except ValueError:
            raise PathTraversalError(f"路径穿越：{abs_path} 不在 {input_dir}")

        rel_path = abs_path.relative_to(ep_resolved).as_posix()
        kind, mime = classify_kind(file)
        size = file.stat().st_size

        found.append(DiscoveredFile(
            abs_path=abs_path,
            rel_path=rel_path,
            kind=kind,
            mime_type=mime,
            size_bytes=size,
        ))

    return found
