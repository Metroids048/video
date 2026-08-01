"""Reference library loader and validator."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml


def _project_root() -> Path:
    """Locate project root by finding knowledge directory."""
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "knowledge" / "references").is_dir():
            return candidate
    raise FileNotFoundError("无法定位 knowledge/references 目录")


def load_catalog() -> list[dict[str, Any]]:
    """Load reference catalog from YAML."""
    catalog_path = _project_root() / "knowledge" / "references" / "catalog.yaml"
    if not catalog_path.is_file():
        raise FileNotFoundError(f"参考目录不存在: {catalog_path}")

    with catalog_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "catalog" not in data:
        raise ValueError("catalog.yaml 必须包含 'catalog' 键")

    return data["catalog"]


def load_patterns() -> list[dict[str, Any]]:
    """Load reference patterns from YAML."""
    patterns_path = _project_root() / "knowledge" / "references" / "patterns.yaml"
    if not patterns_path.is_file():
        raise FileNotFoundError(f"模式库不存在: {patterns_path}")

    with patterns_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "patterns" not in data:
        raise ValueError("patterns.yaml 必须包含 'patterns' 键")

    return data["patterns"]


def load_library() -> dict[str, Any]:
    """Load complete reference library (catalog + patterns)."""
    catalog = load_catalog()
    patterns = load_patterns()

    # Get version from catalog file
    catalog_path = _project_root() / "knowledge" / "references" / "catalog.yaml"
    with catalog_path.open(encoding="utf-8") as f:
        catalog_data = yaml.safe_load(f)

    return {
        "version": catalog_data.get("version", "1.0"),
        "catalog": catalog,
        "patterns": patterns,
    }


def validate_library() -> tuple[bool, list[str]]:
    """Validate reference library against schema.

    Returns:
        (is_valid, error_messages)
    """
    errors: list[str] = []

    try:
        library = load_library()
    except Exception as exc:
        return False, [f"加载知识库失败: {exc}"]

    # Load schema
    schema_path = _project_root() / "schemas" / "reference-library.schema.json"
    if not schema_path.is_file():
        return False, [f"Schema 文件不存在: {schema_path}"]

    try:
        with schema_path.open(encoding="utf-8") as f:
            schema = json.load(f)
    except Exception as exc:
        return False, [f"加载 Schema 失败: {exc}"]

    # Validate against schema
    try:
        jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(library)
    except jsonschema.ValidationError as exc:
        errors.append(f"Schema 验证失败: {exc.message} at {'/'.join(str(p) for p in exc.path)}")
        return False, errors

    # Additional validations
    catalog = library["catalog"]
    patterns = library["patterns"]

    # Check source_id uniqueness
    source_ids = [item["source_id"] for item in catalog]
    if len(source_ids) != len(set(source_ids)):
        duplicates = {sid for sid in source_ids if source_ids.count(sid) > 1}
        errors.append(f"重复的 source_id: {', '.join(duplicates)}")

    # Check URL uniqueness
    urls = [item["url"] for item in catalog]
    if len(urls) != len(set(urls)):
        duplicates = {url for url in urls if urls.count(url) > 1}
        errors.append(f"重复的 URL: {', '.join(duplicates)}")

    # Check pattern_id uniqueness
    pattern_ids = [item["pattern_id"] for item in patterns]
    if len(pattern_ids) != len(set(pattern_ids)):
        duplicates = {pid for pid in pattern_ids if pattern_ids.count(pid) > 1}
        errors.append(f"重复的 pattern_id: {', '.join(duplicates)}")

    # Check pattern source_ids reference valid catalog entries
    valid_source_ids = set(source_ids)
    for pattern in patterns:
        for source_id in pattern.get("source_ids", []):
            if source_id not in valid_source_ids:
                errors.append(
                    f"Pattern {pattern['pattern_id']} 引用了不存在的 source_id: {source_id}"
                )

    return len(errors) == 0, errors


def get_source_by_id(source_id: str) -> dict[str, Any] | None:
    """Get a specific source by ID."""
    catalog = load_catalog()
    for source in catalog:
        if source["source_id"] == source_id:
            return source
    return None


def get_pattern_by_id(pattern_id: str) -> dict[str, Any] | None:
    """Get a specific pattern by ID."""
    patterns = load_patterns()
    for pattern in patterns:
        if pattern["pattern_id"] == pattern_id:
            return pattern
    return None


def find_patterns_by_category(category: str) -> list[dict[str, Any]]:
    """Find all patterns in a given category."""
    patterns = load_patterns()
    return [p for p in patterns if p["category"] == category]


def find_patterns_by_source(source_id: str) -> list[dict[str, Any]]:
    """Find all patterns that reference a given source."""
    patterns = load_patterns()
    return [p for p in patterns if source_id in p.get("source_ids", [])]
