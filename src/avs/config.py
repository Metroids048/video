"""Project configuration loader for Creator OS V2 / AVS engine."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """Configuration loading or validation failed."""


def _load_yaml(path: Path) -> dict[str, Any]:
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
    """Lazy aggregate for the canonical Creator OS configuration surface."""

    _REQUIRED_FILES = [
        "project.yaml",
        "workflow.yaml",
        "platforms.yaml",
        "visual.yaml",
        "audio.yaml",
        "quality.yaml",
        "video-review.yaml",
        "providers.yaml",
        "content-pillars.yaml",
        "creator-workflow.yaml",
        "production-types.yaml",
        "content-formats.yaml",
        "reference-acquisition.yaml",
        "voice.yaml",
    ]

    def __init__(self, root: Path) -> None:
        self._root = root
        self._config_dir = root / "config"
        self._cache: dict[str, dict[str, Any]] = {}

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
    def quality(self) -> dict[str, Any]:
        return self._get("quality.yaml")

    @property
    def video_review(self) -> dict[str, Any]:
        return self._get("video-review.yaml")

    @property
    def providers(self) -> dict[str, Any]:
        return self._get("providers.yaml")

    @property
    def content_pillars(self) -> dict[str, Any]:
        return self._get("content-pillars.yaml")

    @property
    def creator_workflow(self) -> dict[str, Any]:
        return self._get("creator-workflow.yaml")

    @property
    def production_types(self) -> dict[str, Any]:
        return self._get("production-types.yaml")

    @property
    def content_formats(self) -> dict[str, Any]:
        return self._get("content-formats.yaml")

    @property
    def reference_acquisition(self) -> dict[str, Any]:
        return self._get("reference-acquisition.yaml")

    @property
    def voice(self) -> dict[str, Any]:
        return self._get("voice.yaml")

    @property
    def required_config_files(self) -> tuple[str, ...]:
        return tuple(self._REQUIRED_FILES)

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

    @property
    def public_lifecycle(self) -> tuple[str, ...]:
        return tuple(self.workflow.get("workflow", {}).get("public_lifecycle", []))

    def validate_all(self) -> list[str]:
        errors: list[str] = []
        for filename in self._REQUIRED_FILES:
            try:
                self._get(filename)
            except ConfigError as exc:
                errors.append(str(exc))
        return errors


def load_config(root: Path | None = None) -> Config:
    if root is None:
        from avs.cli import _find_project_root
        root = _find_project_root()
    return Config(root)
