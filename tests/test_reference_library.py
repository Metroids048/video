"""Tests for reference library loader and validator."""
from __future__ import annotations

import pytest

from avs.reference.library import (
    find_patterns_by_category,
    find_patterns_by_source,
    get_pattern_by_id,
    get_source_by_id,
    load_catalog,
    load_library,
    load_patterns,
    validate_library,
)


def test_load_catalog() -> None:
    """Test loading reference catalog."""
    catalog = load_catalog()
    assert isinstance(catalog, list)
    assert len(catalog) == 18  # 18 confirmed references

    # Check first entry structure
    first = catalog[0]
    assert first["source_id"] == "REF-001"
    assert first["author"] == "阿柴ChayAI"
    assert first["evidence_level"] == "A"
    assert isinstance(first["page_verified_points"], list)
    assert isinstance(first["can_migrate"], list)
    assert isinstance(first["must_not_copy"], list)


def test_load_patterns() -> None:
    """Test loading reference patterns."""
    patterns = load_patterns()
    assert isinstance(patterns, list)
    assert len(patterns) >= 10  # At least 10 patterns

    # Check first pattern structure
    first = patterns[0]
    assert first["pattern_id"] == "PAT-001"
    assert "category" in first
    assert "rule" in first
    assert "when_to_use" in first
    assert "when_not_to_use" in first
    assert isinstance(first["source_ids"], list)
    assert first["confidence"] in ["high", "medium", "low"]
    assert isinstance(first["machine_constraints"], dict)


def test_load_library() -> None:
    """Test loading complete library."""
    library = load_library()
    assert "version" in library
    assert "catalog" in library
    assert "patterns" in library
    assert len(library["catalog"]) == 18
    assert len(library["patterns"]) >= 10


def test_validate_library_success() -> None:
    """Test library validation passes."""
    is_valid, errors = validate_library()
    assert is_valid is True
    assert len(errors) == 0


def test_source_id_uniqueness() -> None:
    """Test all source IDs are unique."""
    catalog = load_catalog()
    source_ids = [item["source_id"] for item in catalog]
    assert len(source_ids) == len(set(source_ids))


def test_url_uniqueness() -> None:
    """Test all URLs are unique."""
    catalog = load_catalog()
    urls = [item["url"] for item in catalog]
    assert len(urls) == len(set(urls))


def test_pattern_id_uniqueness() -> None:
    """Test all pattern IDs are unique."""
    patterns = load_patterns()
    pattern_ids = [item["pattern_id"] for item in patterns]
    assert len(pattern_ids) == len(set(pattern_ids))


def test_pattern_source_refs_exist() -> None:
    """Test all pattern source_ids reference valid catalog entries."""
    catalog = load_catalog()
    patterns = load_patterns()

    valid_source_ids = {item["source_id"] for item in catalog}

    for pattern in patterns:
        for source_id in pattern["source_ids"]:
            assert source_id in valid_source_ids, (
                f"Pattern {pattern['pattern_id']} references non-existent source {source_id}"
            )


def test_get_source_by_id() -> None:
    """Test retrieving source by ID."""
    source = get_source_by_id("REF-001")
    assert source is not None
    assert source["author"] == "阿柴ChayAI"

    missing = get_source_by_id("REF-999")
    assert missing is None


def test_get_pattern_by_id() -> None:
    """Test retrieving pattern by ID."""
    pattern = get_pattern_by_id("PAT-001")
    assert pattern is not None
    assert pattern["category"] == "workflow"

    missing = get_pattern_by_id("PAT-999")
    assert missing is None


def test_find_patterns_by_category() -> None:
    """Test finding patterns by category."""
    workflow_patterns = find_patterns_by_category("workflow")
    assert len(workflow_patterns) > 0
    assert all(p["category"] == "workflow" for p in workflow_patterns)


def test_find_patterns_by_source() -> None:
    """Test finding patterns by source."""
    patterns = find_patterns_by_source("REF-001")
    assert len(patterns) > 0
    assert all("REF-001" in p["source_ids"] for p in patterns)


def test_all_18_references_present() -> None:
    """Test all 18 confirmed references are in catalog."""
    catalog = load_catalog()
    expected_ids = [f"REF-{i:03d}" for i in range(1, 19)]
    actual_ids = [item["source_id"] for item in catalog]

    for expected_id in expected_ids:
        assert expected_id in actual_ids, f"Missing reference: {expected_id}"


def test_high_confidence_patterns_have_constraints() -> None:
    """Test high-confidence patterns have machine constraints."""
    patterns = load_patterns()
    high_confidence = [p for p in patterns if p["confidence"] == "high"]

    for pattern in high_confidence:
        assert len(pattern["machine_constraints"]) > 0, (
            f"High-confidence pattern {pattern['pattern_id']} should have machine constraints"
        )
