"""tests/test_schemas.py — JSON Schema 加载与校验测试。"""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "schemas"

SCHEMA_FILES = [
    "episode.schema.json",
    "asset-manifest.schema.json",
    "reference-recipe.schema.json",
    "script.schema.json",
    "storyboard.schema.json",
    "timeline.schema.json",
    "qa-report.schema.json",
    "delivery-manifest.schema.json",
]


class TestSchemaFilesExist:
    @pytest.mark.parametrize("filename", SCHEMA_FILES)
    def test_file_exists(self, filename: str):
        path = SCHEMAS_DIR / filename
        assert path.exists(), f"Schema 文件缺失: {path}"

    @pytest.mark.parametrize("filename", SCHEMA_FILES)
    def test_file_is_valid_json(self, filename: str):
        path = SCHEMAS_DIR / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"{filename} 根节点不是 object"
        assert "$schema" in data, f"{filename} 缺少 $schema 字段"
        assert "title" in data, f"{filename} 缺少 title 字段"


class TestEpisodeSchema:
    @pytest.fixture()
    def schema(self) -> dict:
        return json.loads((SCHEMAS_DIR / "episode.schema.json").read_text(encoding="utf-8"))

    def test_valid_episode(self, schema: dict):
        data = {
            "id": "EP-0001",
            "mode": "REFERENCE_ADAPT",
            "publishable": True,
            "status": "CREATED",
            "platforms": ["douyin"],
            "completed_stages": [],
            "blocked_stage": None,
            "last_error": None,
            "artifacts": {},
            "title": None,
            "created_at": "2026-07-20T13:00:00+00:00",
            "updated_at": "2026-07-20T13:00:00+00:00",
        }
        jsonschema.validate(data, schema)  # 不应抛异常

    def test_valid_blocked_stage(self, schema: dict):
        data = {
            "id": "EP-0001",
            "mode": "REFERENCE_ADAPT",
            "publishable": True,
            "status": "INGESTED",
            "platforms": ["douyin"],
            "completed_stages": ["ingest"],
            "blocked": True,
            "blocked_stage": "analyze",
            "last_error": "缺 Provider",
            "artifacts": {},
            "created_at": "2026-07-20T13:00:00+00:00",
            "updated_at": "2026-07-20T13:00:00+00:00",
        }
        jsonschema.validate(data, schema)

    def test_missing_required_field(self, schema: dict):
        data = {"id": "EP-0001"}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_invalid_status(self, schema: dict):
        data = {
            "id": "EP-0001",
            "mode": "REFERENCE_ADAPT",
            "publishable": True,
            "status": "INVALID_STATUS",
            "platforms": ["douyin"],
            "completed_stages": [],
            "last_error": None,
            "artifacts": {},
            "created_at": "2026-07-20T13:00:00+00:00",
            "updated_at": "2026-07-20T13:00:00+00:00",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_invalid_id_pattern(self, schema: dict):
        data = {
            "id": "lowercase",  # 非法
            "mode": "REFERENCE_ADAPT",
            "publishable": True,
            "status": "CREATED",
            "platforms": ["douyin"],
            "completed_stages": [],
            "last_error": None,
            "artifacts": {},
            "created_at": "2026-07-20T13:00:00+00:00",
            "updated_at": "2026-07-20T13:00:00+00:00",
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, schema)

    def test_reference_clone_publishable_false(self, schema: dict):
        """Schema 层不强制业务规则，但 publishable=false 必须合法。"""
        data = {
            "id": "RC-0001",
            "mode": "REFERENCE_CLONE",
            "publishable": False,
            "status": "CREATED",
            "platforms": ["douyin"],
            "completed_stages": [],
            "last_error": None,
            "artifacts": {},
            "created_at": "2026-07-20T13:00:00+00:00",
            "updated_at": "2026-07-20T13:00:00+00:00",
        }
        jsonschema.validate(data, schema)  # 不应抛异常
