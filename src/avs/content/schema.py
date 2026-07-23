"""src/avs/content/schema.py — Script/Storyboard Schema 校验。"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import jsonschema

log = logging.getLogger(__name__)

_SCRIPT_SCHEMA = Path(__file__).resolve().parents[3] / "schemas" / "script.schema.json"
_STORYBOARD_SCHEMA = Path(__file__).resolve().parents[3] / "schemas" / "storyboard.schema.json"


def _load_schema(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def validate_script(data: dict[str, Any]) -> None:
    """校验 script.json；失败时抛出 jsonschema.ValidationError。"""
    schema = _load_schema(_SCRIPT_SCHEMA)
    jsonschema.validate(data, schema)


def validate_storyboard(data: dict[str, Any]) -> None:
    """校验 storyboard.json；失败时抛出 jsonschema.ValidationError。"""
    schema = _load_schema(_STORYBOARD_SCHEMA)
    jsonschema.validate(data, schema)


def script_path(episode_dir: Path) -> Path:
    return episode_dir / "work" / "content" / "script.json"


def storyboard_path(episode_dir: Path) -> Path:
    return episode_dir / "work" / "content" / "storyboard.json"


def load_script(episode_dir: Path) -> dict[str, Any]:
    """加载并校验 script.json。"""
    p = script_path(episode_dir)
    if not p.exists():
        raise FileNotFoundError(f"script.json 不存在: {p}")
    with p.open(encoding="utf-8") as fh:
        data = json.load(fh)
    validate_script(data)
    return data


def load_storyboard(episode_dir: Path) -> dict[str, Any]:
    """加载并校验 storyboard.json。"""
    p = storyboard_path(episode_dir)
    if not p.exists():
        raise FileNotFoundError(f"storyboard.json 不存在: {p}")
    with p.open(encoding="utf-8") as fh:
        data = json.load(fh)
    validate_storyboard(data)
    return data


def save_script(episode_dir: Path, data: dict[str, Any]) -> Path:
    """校验并保存 script.json。"""
    validate_script(data)
    p = script_path(episode_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        tmp.replace(p)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise OSError(f"script.json 写入失败: {exc}") from exc
    return p


def save_storyboard(episode_dir: Path, data: dict[str, Any]) -> Path:
    """校验并保存 storyboard.json。"""
    validate_storyboard(data)
    p = storyboard_path(episode_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        tmp.replace(p)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise OSError(f"storyboard.json 写入失败: {exc}") from exc
    return p
