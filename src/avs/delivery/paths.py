"""Safe path helpers for self-contained delivery packages."""
from __future__ import annotations

from pathlib import Path


def delivery_relative(ep_dir: Path, path: Path) -> str:
    resolved_episode = ep_dir.resolve()
    resolved_path = path.resolve()
    relative = resolved_path.relative_to(resolved_episode)
    if not relative.parts or relative.parts[0] != "delivery" or ".." in relative.parts:
        raise ValueError(f"交付文件必须位于 delivery/: {path}")
    return relative.as_posix()


def safe_delivery_target(ep_dir: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"非法交付相对路径: {relative}")
    target = (ep_dir / "delivery" / relative).resolve()
    target.relative_to((ep_dir / "delivery").resolve())
    return target
