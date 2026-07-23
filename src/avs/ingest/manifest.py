"""src/avs/ingest/manifest.py — 读写 work/asset-manifest.json + Schema 校验。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from avs.ingest.errors import ManifestError

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "asset-manifest.schema.json"


def _load_schema() -> dict:
    if not _SCHEMA_PATH.exists():
        raise ManifestError(f"Schema 文件缺失: {_SCHEMA_PATH}")
    with _SCHEMA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def manifest_path(episode_dir: Path) -> Path:
    return episode_dir / "work" / "asset-manifest.json"


def save_manifest(episode_dir: Path, episode_id: str, assets: list[dict]) -> Path:
    """将 asset 列表写入 work/asset-manifest.json；写前做 Schema 校验。"""
    doc = {
        "episode_id": episode_id,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "assets": assets,
    }
    _validate(doc)

    out = manifest_path(episode_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
        tmp.replace(out)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise ManifestError(f"写入 asset-manifest.json 失败: {exc}") from exc
    return out


def load_manifest(episode_dir: Path) -> dict[str, Any]:
    """加载并校验 asset-manifest.json；不存在时抛出 ManifestError。"""
    path = manifest_path(episode_dir)
    if not path.exists():
        raise ManifestError(f"asset-manifest.json 不存在: {path}")
    with path.open(encoding="utf-8") as fh:
        doc = json.load(fh)
    _validate(doc)
    return doc


def _validate(doc: dict) -> None:
    try:
        schema = _load_schema()
        jsonschema.validate(doc, schema)
    except jsonschema.ValidationError as exc:
        raise ManifestError(f"asset-manifest Schema 校验失败: {exc.message}") from exc
