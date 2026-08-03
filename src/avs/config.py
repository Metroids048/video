"""src/avs/config.py — 项目配置加载器。

从 config/ 目录读取 YAML；缺文件时抛出明确错误，不静默忽略。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """配置加载或校验失败。"""


def _load_yaml(path: Path) -> dict[str, Any]:
    """加载单个 YAML 文件；不存在时抛出 ConfigError。"""
    if not path.exists():
        raise ConfigError(f"配置文件缺失: {path}")
    try:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ConfigError(f"YAML 解析失败 ({path}): {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"配置文件根节点必须是 mapping: {path}")
    return data


class Config:
    """项目配置聚合。懒加载，首次访问属性时读取文件。"""

    _REQUIRED_FILES = [
        "project.yaml",
        "workflow.yaml",
        "platforms.yaml",
        "visual.yaml",
        "audio.yaml",
        "providers.yaml",
        "content-pillars.yaml",
        "creator-workflow.yaml",
    ]

    def __init__(self, root: Path) -> None:
        self._root = root
        self._config_dir = root / "config"
        self._cache: dict[str, dict[str, Any]] = {}

    # ── 单文件访问 ────────────────────────────────────────────────────

    def _get(self, filename: str) -> dict[str, Any]:
        if filename not in self._cache:
            self._cache[filename] = _load_yaml(self._config_dir / filename)
        return self._cache[filename]

    @property
    def project(self) -> dict[str, Any]:
        return self._get("project.yaml")

    @property
    def workflow(self) -> dict[str, Any]:
        return self._get("workflow.yaml")

    @property
    def platforms(self) -> dict[str, Any]:
        return self._get("platforms.yaml")

    @property
    def visual(self) -> dict[str, Any]:
        return self._get("visual.yaml")

    @property
    def audio(self) -> dict[str, Any]:
        return self._get("audio.yaml")

    @property
    def providers(self) -> dict[str, Any]:
        return self._get("providers.yaml")

    @property
    def content_pillars(self) -> dict[str, Any]:
        return self._get("content-pillars.yaml")

    @property
    def creator_workflow(self) -> dict[str, Any]:
        """Account-level content and monetization contract."""
        return self._get("creator-workflow.yaml")

    @property
    def required_config_files(self) -> tuple[str, ...]:
        """Expose the canonical config contract for tests and diagnostics."""
        return tuple(self._REQUIRED_FILES)

    # ── 便捷属性 ──────────────────────────────────────────────────────

    @property
    def episodes_root(self) -> Path:
        rel = self.project.get("project", {}).get("episodes_root", "episodes")
        return self._root / rel

    @property
    def episode_id_pattern(self) -> str:
        return self.project.get("episode_id_pattern", r"^[A-Z0-9][A-Z0-9_-]{1,63}$")

    @property
    def allowed_transitions(self) -> dict[str, list[str]]:
        return self.workflow.get("workflow", {}).get("transitions", {})

    # ── 全量校验 ──────────────────────────────────────────────────────

    def validate_all(self) -> list[str]:
        """加载所有必需配置文件，返回错误列表（空 = 全部通过）。"""
        errors: list[str] = []
        for filename in self._REQUIRED_FILES:
            try:
                self._get(filename)
            except ConfigError as exc:
                errors.append(str(exc))
        return errors


def load_config(root: Path | None = None) -> Config:
    """获取 Config 实例。root 默认为当前目录向上查找 AGENTS.md 所在目录。"""
    if root is None:
        from avs.cli import _find_project_root  # 避免循环导入
        root = _find_project_root()
    return Config(root)
