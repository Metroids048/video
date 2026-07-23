"""src/avs/paths.py — Episode 目录骨架与路径解析。

所有路径使用 pathlib.Path；不使用字符串拼接，防止路径穿越。
"""
from __future__ import annotations

import re
from pathlib import Path

# Episode ID 合法格式（与 config/project.yaml 保持一致）
_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,63}$")

# Episode 根目录下的子目录分区
_LIFECYCLE_DIRS = ("inbox", "active", "completed", "archived")


class PathError(Exception):
    """路径操作失败（非法 ID、路径穿越等）。"""


def validate_episode_id(episode_id: str) -> None:
    """校验 Episode ID 格式；不合法时抛出 PathError。"""
    if not _ID_PATTERN.match(episode_id):
        raise PathError(
            f"非法 Episode ID: {episode_id!r}。"
            "只允许大写字母、数字、下划线和连字符，长度 2–64，且首字符为大写字母或数字。"
        )


def episode_dir(episodes_root: Path, episode_id: str, *, lifecycle: str = "active") -> Path:
    """返回 Episode 工作目录的绝对 Path，但不创建目录。

    同时进行 ID 格式校验和路径穿越检测。
    """
    validate_episode_id(episode_id)
    if lifecycle not in _LIFECYCLE_DIRS:
        raise PathError(f"未知 lifecycle 分区: {lifecycle!r}")

    base = episodes_root.resolve()
    target = (base / lifecycle / episode_id).resolve()

    # 防止路径穿越：目标必须在 base 内
    try:
        target.relative_to(base)
    except ValueError:
        raise PathError(f"路径穿越检测失败: {target} 不在 {base} 内")

    return target


def create_episode_skeleton(episode_dir: Path) -> None:
    """在 episode_dir 下创建规范子目录骨架（幂等）。

    目录结构：
        input/reference/
        input/screen/
        input/images/
        input/audio/
        work/reference/
        work/content/
        work/prepared/
        work/motion/
        renders/
        delivery/assets-used/
        delivery/motion-graphics/
        delivery/publish/
        logs/
    """
    subdirs = [
        "input/reference",
        "input/screen",
        "input/images",
        "input/audio",
        "work/reference",
        "work/content",
        "work/prepared",
        "work/motion",
        "renders",
        "delivery/assets-used",
        "delivery/motion-graphics",
        "delivery/publish",
        "logs",
    ]
    for rel in subdirs:
        (episode_dir / rel).mkdir(parents=True, exist_ok=True)


def find_episode_dir(episodes_root: Path, episode_id: str) -> Path | None:
    """在所有 lifecycle 分区中搜索 episode_id，返回第一个命中的目录或 None。"""
    validate_episode_id(episode_id)
    for lifecycle in _LIFECYCLE_DIRS:
        candidate = episodes_root / lifecycle / episode_id
        if candidate.is_dir():
            return candidate.resolve()
    return None


def episode_json_path(ep_dir: Path) -> Path:
    """返回 episode.json 的绝对路径。"""
    return ep_dir / "episode.json"
