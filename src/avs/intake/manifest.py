"""Unified input manifest and the explicit missing-material gate.

``asset-manifest.json`` remains the legacy ingest contract.  This module is
the richer contract consumed by the active multimodal workflow.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import jsonschema

from avs.ingest.errors import ManifestError

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "input-manifest.schema.json"


class InputCompletenessError(ManifestError):
    """A required user asset is missing or unusable."""

    def __init__(self, missing: list[dict[str, Any]]) -> None:
        self.missing = missing
        detail = "; ".join(
            f"缺少：{item['source_path']}；影响：{item.get('impact', '无法完成对应表达')}；"
            f"处理：{item.get('action', '请补充素材或明确允许删除该表达')}"
            for item in missing
        )
        super().__init__(detail or "输入素材不完整")


def input_manifest_path(episode_dir: Path) -> Path:
    return episode_dir / "work" / "input-manifest.json"


def _validate(doc: dict[str, Any]) -> None:
    try:
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft7Validator(
            schema, format_checker=jsonschema.FormatChecker()
        ).validate(doc)
    except (jsonschema.ValidationError, jsonschema.SchemaError) as exc:
        raise ManifestError(f"input-manifest Schema 校验失败: {exc}") from exc


def save_input_manifest(episode_dir: Path, episode_id: str, assets: list[dict[str, Any]]) -> Path:
    doc = {
        "episode_id": episode_id,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "assets": assets,
    }
    _validate(doc)
    out = input_manifest_path(episode_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(out)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise ManifestError(f"写入 input-manifest.json 失败: {exc}") from exc
    return out


def load_input_manifest(episode_dir: Path) -> dict[str, Any]:
    path = input_manifest_path(episode_dir)
    if not path.is_file():
        raise ManifestError(f"input-manifest.json 不存在: {path}")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError(f"input-manifest.json 不是有效 JSON: {exc}") from exc
    _validate(doc)
    return doc


def build_input_manifest(episode_id: str, assets: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map legacy ingest records into the explicit multimodal contract.

    Media assets are must-use by default because silently dropping a supplied
    screenshot or recording is unsafe.  Callers can override this with an
    explicit user manifest or an approved exclusion record.
    """
    result: list[dict[str, Any]] = []
    for asset in assets:
        kind = str(asset.get("kind", "unknown"))
        source_type = {
            "image": "screenshot",
            "video": "recording",
            "audio": "audio",
            "text": "text",
            "document": "document",
            "link": "link",
        }.get(kind, "unknown")
        result.append(
            {
                "asset_id": str(asset["asset_id"]),
                "source_path": str(asset["source_path"]),
                "working_path": asset.get("working_path"),
                "source_type": source_type,
                "user_note": asset.get("user_note"),
                "must_use": bool(asset.get("must_use", kind in {"image", "video", "audio"})),
                "sha256": str(asset.get("sha256", "0" * 64)),
                "audio_role": asset.get("audio_role"),
                "original_width": asset.get("original_width", asset.get("width")),
                "original_height": asset.get("original_height", asset.get("height")),
                "duration": asset.get("duration"),
                "proxy_path": asset.get("proxy_path", asset.get("working_path")),
                "proxy_width": asset.get("proxy_width"),
                "proxy_height": asset.get("proxy_height"),
                "status": str(asset.get("status", "ok")),
                "missing_reason": asset.get("missing_reason"),
            }
        )
    return result


def assert_input_complete(
    manifest: dict[str, Any],
    *,
    approved_exclusions: Iterable[str] = (),
) -> None:
    """Fail closed when a must-use item is absent, corrupt, or unsupported."""
    excluded = set(approved_exclusions)
    missing: list[dict[str, Any]] = []
    for asset in manifest.get("assets", []):
        if not asset.get("must_use") or asset.get("asset_id") in excluded:
            continue
        status = asset.get("status", "ok")
        if status != "ok" or not asset.get("working_path"):
            missing.append(
                {
                    "asset_id": asset.get("asset_id"),
                    "source_path": asset.get("source_path"),
                    "impact": asset.get("missing_reason") or "无法证明对应产品事实",
                    "action": "补充素材或明确批准排除该素材",
                }
            )
    if missing:
        raise InputCompletenessError(missing)
