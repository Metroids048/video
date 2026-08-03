"""Reference pattern selection with concrete pattern IDs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
import jsonschema

_SCHEMA = Path(__file__).resolve().parents[3] / "schemas" / "reference-selection.schema.json"


def _patterns_path() -> Path:
    return Path(__file__).resolve().parents[3] / "knowledge" / "references" / "patterns.yaml"


def load_patterns(path: Path | None = None) -> list[dict[str, Any]]:
    source = path or _patterns_path()
    if not source.is_file():
        return []
    doc = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    return list(doc.get("patterns", []))


def select_reference_patterns(
    episode_id: str,
    *,
    platform: str = "douyin",
    pattern_ids: list[str] | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    patterns = load_patterns(path)
    by_id = {item.get("pattern_id"): item for item in patterns}
    chosen = pattern_ids or ["PAT-004", "PAT-009", "PAT-011"]
    selections = []
    for pattern_id in chosen:
        if pattern_id not in by_id:
            raise ValueError(f"Reference pattern 不存在: {pattern_id}")
        category = by_id[pattern_id].get("category", "structure")
        applies = ["hook"] if pattern_id == "PAT-004" else ["shot-001", "shot-002"]
        if category == "captions":
            applies = ["captions", "qa"]
        selections.append({
            "pattern_id": pattern_id,
            "applies_to": applies,
            "reason": f"{platform} 平台采用 {pattern_id} 的 {category} 规则",
        })
    return {"episode_id": episode_id, "selections": selections}


def save_reference_selection(episode_dir: Path, selection: dict[str, Any]) -> Path:
    jsonschema.Draft7Validator(json.loads(_SCHEMA.read_text(encoding="utf-8"))).validate(selection)
    path = episode_dir / "work" / "content" / "reference-selection.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(selection, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
