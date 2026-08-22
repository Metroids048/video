"""Atomic corpus storage, idempotent merge and M1 audit."""
from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

import jsonschema

from .models import AuditReport, AttemptRecord, VideoRecord


SCHEMA_DIR = Path(__file__).resolve().parents[4] / "schemas"


def _json_default(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "value"):
        return value.value
    raise TypeError(type(value).__name__)


def _atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def load_catalog(root: Path) -> list[dict[str, Any]]:
    path = root / "catalog.jsonl"
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_channel(root: Path) -> dict[str, Any]:
    path = root / "channel.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _merge_video(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in incoming.items():
        if value is not None and value != "":
            merged[key] = value
    if existing.get("extraction_status") not in {None, "DISCOVERED"}:
        merged["extraction_status"] = existing["extraction_status"]
    return merged


def write_corpus(
    root: Path,
    *,
    channel: dict[str, Any],
    videos: Iterable[VideoRecord | dict[str, Any]],
    provider: str,
    pagination_complete: bool = True,
    duplicates: int = 0,
    unknown_items: int = 0,
    attempts: Iterable[AttemptRecord | dict[str, Any]] = (),
    force: bool = False,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    merged: dict[str, dict[str, Any]] = {} if force else {row["video_id"]: row for row in load_catalog(root)}
    incoming_duplicates = 0
    for item in videos:
        row = item.to_dict() if isinstance(item, VideoRecord) else dict(item)
        video_id = row.get("video_id")
        if not video_id:
            unknown_items += 1
            continue
        if video_id in merged:
            incoming_duplicates += 1
            merged[video_id] = _merge_video(merged[video_id], row)
        else:
            merged[video_id] = row
    catalog = list(merged.values())
    catalog.sort(key=lambda row: (row.get("published_at") or "", row["video_id"]), reverse=True)
    _atomic_write(root / "channel.json", json.dumps(channel, ensure_ascii=False, indent=2) + "\n")
    _atomic_write(root / "catalog.jsonl", "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in catalog))
    status_counts = Counter(row.get("extraction_status", "FAILED_UNKNOWN") for row in catalog)
    known_statuses = (
        "DISCOVERED", "PRIVATE", "DELETED", "UNAVAILABLE", "BLOCKED_BY_YOUTUBE",
        "RETRYABLE_FAILED", "FAILED_UNKNOWN", "CAPTION_PENDING", "CAPTION_OK",
        "CAPTION_UNAVAILABLE", "MEDIA_PENDING", "MEDIA_OK", "ASR_PENDING", "ASR_OK",
        "TRANSCRIPT_NORMALIZED", "TRANSCRIPT_QA_PASSED",
    )
    manifest = {
        "schema_version": "1.0",
        "channel_slug": channel.get("handle") or channel.get("channel_id"),
        "channel_url": channel.get("canonical_url"),
        "generated_at": channel.get("discovered_at"),
        "extractor_version": channel.get("extractor_version"),
        "provider": provider,
        "pagination_complete": pagination_complete,
        "counts": {
            "discovered": len(catalog),
            "unique_ids": len(catalog),
            "duplicates": duplicates + incoming_duplicates,
            "unknown": unknown_items,
            **{key: status_counts.get(key, 0) for key in known_statuses},
        },
        "videos": [
            {"video_id": row["video_id"], "status": row.get("extraction_status", "FAILED_UNKNOWN"),
             "attempts": row.get("attempts", [])}
            for row in catalog
        ],
        "attempts": [a.to_dict() if isinstance(a, AttemptRecord) else a for a in attempts],
    }
    _atomic_write(root / "corpus_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2, default=_json_default) + "\n")


def audit_corpus(root: Path) -> AuditReport:
    errors: list[str] = []
    channel_path = root / "channel.json"
    manifest_path = root / "corpus_manifest.json"
    if not channel_path.exists() or not manifest_path.exists():
        return AuditReport(False, {"files_present": False}, {}, ["channel.json 或 corpus_manifest.json 缺失"])
    try:
        channel = json.loads(channel_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        jsonschema.validate(channel, json.loads((SCHEMA_DIR / "youtube-channel.schema.json").read_text(encoding="utf-8")))
        jsonschema.validate(manifest, json.loads((SCHEMA_DIR / "youtube-corpus-manifest.schema.json").read_text(encoding="utf-8")))
        video_schema = json.loads((SCHEMA_DIR / "youtube-video.schema.json").read_text(encoding="utf-8"))
        for row in load_catalog(root):
            jsonschema.validate(row, video_schema)
    except Exception as exc:  # noqa: BLE001
        return AuditReport(False, {"schema_valid": False}, {}, [f"schema 校验失败: {exc}"])
    catalog = load_catalog(root)
    ids = [row.get("video_id") for row in catalog]
    counts = Counter(row.get("extraction_status", "FAILED_UNKNOWN") for row in catalog)
    manifest_ids = [row.get("video_id") for row in manifest.get("videos", [])]
    manifest_counts = manifest.get("counts", {})
    allowed_statuses = tuple(key for key in manifest_counts if key not in {"discovered", "unique_ids", "duplicates", "unknown"})
    coverage_total = sum(int(manifest_counts.get(status, 0)) for status in allowed_statuses)
    checks = {
        "schema_valid": True,
        "unique_video_ids": len(ids) == len(set(ids)),
        "manifest_coverage": set(ids) == set(manifest_ids),
        "pagination_complete": bool(manifest.get("pagination_complete")),
        "count_consistent": manifest_counts.get("discovered") == len(catalog) and coverage_total == len(catalog),
        "failed_unknown_zero": counts.get("FAILED_UNKNOWN", 0) == 0,
        "unknown_zero": manifest_counts.get("unknown", 0) == 0,
    }
    for name, passed in checks.items():
        if not passed:
            errors.append(name)
    return AuditReport(all(checks.values()), checks, dict(counts), errors)


def update_video_state(root: Path, video_id: str, *, extraction_status: str,
                       attempts: list[dict[str, Any]] | None = None) -> None:
    """Persist one video state without changing other discovery records."""
    channel = load_channel(root)
    rows = load_catalog(root)
    changed = False
    for row in rows:
        if row.get("video_id") == video_id:
            row["extraction_status"] = extraction_status
            if attempts is not None:
                row["attempts"] = attempts
            changed = True
            break
    if not changed:
        raise KeyError(f"video_id not found in catalog: {video_id}")
    write_corpus(root, channel=channel, videos=rows, provider="transcript", force=True,
                 pagination_complete=True, attempts=attempts or [])
