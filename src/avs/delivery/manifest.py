"""Delivery manifest records and Schema validation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema

from avs.delivery.paths import delivery_relative


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(ep_dir: Path, path: Path, *, required: bool) -> dict[str, Any]:
    return {
        "name": path.relative_to(ep_dir / "delivery").as_posix(),
        "path": delivery_relative(ep_dir, path),
        "required": required,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def validate_manifest(ep_dir: Path, payload: dict[str, Any]) -> None:
    root: Path | None = None
    for candidate in (ep_dir, *ep_dir.parents):
        if (candidate / "schemas" / "delivery-manifest.schema.json").is_file():
            root = candidate
            break
    if root is None:
        raise FileNotFoundError("无法定位 schemas/delivery-manifest.schema.json")
    schema = json.loads((root / "schemas" / "delivery-manifest.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(payload)

    for item in payload["files"]:
        path = ep_dir / Path(item["path"])
        if not path.is_file():
            raise FileNotFoundError(f"清单文件不存在: {item['path']}")
        if path.stat().st_size != item["size_bytes"] or sha256_file(path) != item["sha256"]:
            raise ValueError(f"清单文件校验失败: {item['path']}")
