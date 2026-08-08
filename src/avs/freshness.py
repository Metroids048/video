"""src/avs/freshness.py — 产物新鲜度判定。

流水线的每一层都缓存产物以避免重复渲染，但**"产物存在"不等于"产物是当前的"**。
存在性缓存会让上游改动被静默丢弃：storyboard / timeline / 脚本已经是新的，
`renders/*.mp4` 仍是旧的，而每一层都报告成功。症状是"报告说改了，视频没改"。

本模块提供统一的判定：产物只有在**不早于全部上游来源**时才可复用。

配套的 `write_text_if_changed` 同样重要：若某一层每次运行都重写内容相同的文件，
它的 mtime 会不断刷新，使下游永远判定为过期，从而退化成"每次全量重渲染"。
两者必须成对使用，缓存链才既不陈旧也不失效。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)


def _file_mtime(path: Path) -> float | None:
    """返回 mtime；路径不存在或不可读时返回 None（视为无约束）。"""
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def newest_source_mtime(sources: Iterable[Path]) -> float | None:
    """全部来源中最新的 mtime。目录按递归文件展开；不存在的来源被忽略。"""
    newest: float | None = None
    for source in sources:
        try:
            is_dir = source.is_dir()
        except OSError:
            continue
        if is_dir:
            try:
                children = [child for child in source.rglob("*") if child.is_file()]
            except OSError:
                children = []
            stamps = [stamp for stamp in (_file_mtime(child) for child in children) if stamp]
        else:
            stamps = [stamp for stamp in (_file_mtime(source),) if stamp]
        for stamp in stamps:
            if newest is None or stamp > newest:
                newest = stamp
    return newest


def is_stale(artifact: Path, sources: Iterable[Path]) -> bool:
    """产物是否需要重建。

    缺失的产物必然过期；任一来源比产物新即过期。来源全部缺失时视为不过期，
    避免在上游本就可选（例如无字幕、无 BGM）的场景下陷入无休止重建。
    """
    built_at = _file_mtime(artifact)
    if built_at is None:
        return True
    newest = newest_source_mtime(sources)
    return newest is not None and newest > built_at


def stale_reason(artifact: Path, sources: Iterable[Path]) -> str | None:
    """人类可读的过期原因，用于日志；不过期时返回 None。"""
    built_at = _file_mtime(artifact)
    if built_at is None:
        return f"{artifact.name} 不存在"
    for source in sources:
        stamp = newest_source_mtime([source])
        if stamp is not None and stamp > built_at:
            return f"{source.name} 比 {artifact.name} 新"
    return None


def write_text_if_changed(path: Path, text: str, *, encoding: str = "utf-8") -> bool:
    """内容有变化时原子写入并返回 True；内容相同则不触碰文件（保持 mtime）。

    保持 mtime 是关键：无条件重写会让下游产物每次都判定为过期。
    """
    try:
        if path.read_text(encoding=encoding) == text:
            return False
    except (OSError, UnicodeDecodeError):
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding=encoding)
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return True
