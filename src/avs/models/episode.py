"""src/avs/models/episode.py — Episode 数据模型与 episode.json 读写。

时间一律使用带时区 ISO 8601 字符串（datetime.timezone.utc）。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from avs.state import EpisodeStatus, assert_transition

# Schema 路径（相对于此文件向上三级到项目根）
_SCHEMA_REL = Path(__file__).resolve().parents[3] / "schemas" / "episode.schema.json"
_PIPELINE_ORDER = {
    status.value: index
    for index, status in enumerate((
        EpisodeStatus.CREATED,
        EpisodeStatus.INGESTED,
        EpisodeStatus.REFERENCE_READY,
        EpisodeStatus.CONTENT_READY,
        EpisodeStatus.ASSETS_READY,
        EpisodeStatus.TIMELINE_READY,
        EpisodeStatus.ROUGH_CUT_READY,
        EpisodeStatus.QA_PASSED,
        EpisodeStatus.DELIVERY_READY,
    ))
}
_ACTIVE_STAGE_ORDER = (
    "ingest", "analyze", "plan", "preview", "visual-review",
    "final-render", "qa", "approve", "delivery", "export",
)
_BLOCKED_STAGES = frozenset(_ACTIVE_STAGE_ORDER)
_LEGACY_STAGE_STATUS = {
    "ingest": EpisodeStatus.CREATED,
    "analyze": EpisodeStatus.INGESTED,
    "plan": EpisodeStatus.INGESTED,
    "preview": EpisodeStatus.CONTENT_READY,
    "visual-review": EpisodeStatus.TIMELINE_READY,
    "final-render": EpisodeStatus.TIMELINE_READY,
    "qa": EpisodeStatus.ROUGH_CUT_READY,
    "approve": EpisodeStatus.QA_PASSED,
    "delivery": EpisodeStatus.QA_PASSED,
    "export": EpisodeStatus.DELIVERY_READY,
}


def _now_iso() -> str:
    """当前时间，UTC，带时区 ISO 8601。"""
    return datetime.now(tz=timezone.utc).isoformat()


def _load_schema() -> dict[str, Any]:
    if not _SCHEMA_REL.exists():
        raise FileNotFoundError(f"Schema 文件缺失: {_SCHEMA_REL}")
    with _SCHEMA_REL.open(encoding="utf-8") as fh:
        return json.load(fh)


class EpisodeValidationError(Exception):
    """episode.json Schema 校验失败。"""


class EpisodeModel:
    """episode.json 的读写与状态转换封装。"""

    # REFERENCE_CLONE 强制 publishable=false
    _UNPUBLISHABLE_MODES = frozenset({"REFERENCE_CLONE"})

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    # ── 属性快捷方式 ─────────────────────────────────────────────────

    @property
    def id(self) -> str:
        return self._data["id"]

    @property
    def status(self) -> str:
        return self._data["status"]

    @property
    def mode(self) -> str:
        return self._data["mode"]

    @property
    def input_mode(self) -> str:
        return str(self._data.get("input_mode", "multimodal"))

    @property
    def publishable(self) -> bool:
        return bool(self._data["publishable"])

    @property
    def last_error(self) -> str | None:
        return self._data.get("last_error")

    @property
    def blocked(self) -> bool:
        return bool(self._data.get("blocked", False))

    @property
    def blocked_stage(self) -> str | None:
        value = self._data.get("blocked_stage")
        return str(value) if value is not None else None

    @property
    def completed_stages(self) -> list[str]:
        return list(self._data.get("completed_stages", []))

    @property
    def artifacts(self) -> dict[str, str]:
        return dict(self._data.get("artifacts", {}))

    # ── 工厂方法 ──────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        episode_id: str,
        *,
        mode: str = "REFERENCE_ADAPT",
        platforms: list[str] | None = None,
        input_mode: str = "multimodal",
    ) -> "EpisodeModel":
        """构建全新 Episode 数据（不写磁盘）。"""
        if platforms is None:
            platforms = ["douyin", "xiaohongshu"]

        publishable = mode not in cls._UNPUBLISHABLE_MODES
        now = _now_iso()

        data: dict[str, Any] = {
            "id": episode_id,
            "mode": mode,
            "input_mode": input_mode,
            "publishable": publishable,
            "status": EpisodeStatus.CREATED,
            "platforms": platforms,
            "completed_stages": [],
            "last_error": None,
            "blocked": False,
            "blocked_stage": None,
            "artifacts": {},
            "title": None,
            "created_at": now,
            "updated_at": now,
        }
        return cls(data)

    # ── 读写 ──────────────────────────────────────────────────────────

    @classmethod
    def load(cls, path: Path) -> "EpisodeModel":
        """从 episode.json 加载并 Schema 校验。"""
        if not path.exists():
            raise FileNotFoundError(f"episode.json 不存在: {path}")
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        instance = cls(data)
        instance.validate_schema()
        return instance

    def save(self, path: Path) -> None:
        """将当前状态写入 episode.json（原子写：先写临时文件再重命名）。"""
        self._data["updated_at"] = _now_iso()
        self.validate_schema()
        tmp = path.with_suffix(".json.tmp")
        try:
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(self._data, fh, ensure_ascii=False, indent=2)
            tmp.replace(path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    # ── 状态转换 ──────────────────────────────────────────────────────

    def transition(self, target: str, *, force: bool = False) -> None:
        """执行状态转换；非法时抛出 TransitionError。"""
        assert_transition(self.status, target, force=force)
        self._data["status"] = target
        self._data["updated_at"] = _now_iso()

    def ensure_stage(self, stage: str, target: str) -> bool:
        """推进到阶段目标；已完成且处于后续状态时幂等返回。"""
        if self.status == target:
            return False
        current_rank = _PIPELINE_ORDER.get(self.status)
        target_rank = _PIPELINE_ORDER.get(target)
        if (
            stage in self.completed_stages
            and current_rank is not None
            and target_rank is not None
            and current_rank > target_rank
        ):
            return False
        self.transition(target)
        return True

    def fail(self, reason: str) -> None:
        """将状态置为 FAILED 并记录原因。"""
        if self.status != EpisodeStatus.FAILED:
            assert_transition(self.status, EpisodeStatus.FAILED)
            self._data["status"] = EpisodeStatus.FAILED
        self._data["last_error"] = reason
        self._data["updated_at"] = _now_iso()

    def block(self, reason: str, *, stage: str, waiting_for_input: bool = False) -> None:
        """Record a recoverable pause without committing the blocked stage."""
        if stage not in _BLOCKED_STAGES:
            raise EpisodeValidationError(f"未知的可恢复阶段: {stage}")
        if waiting_for_input and self.status != EpisodeStatus.WAITING_FOR_INPUT:
            self.transition(EpisodeStatus.WAITING_FOR_INPUT)
        self._data["blocked"] = True
        self._data["blocked_stage"] = stage
        self._data["last_error"] = reason
        self._data["updated_at"] = _now_iso()

    def clear_block(self, *, stage: str) -> None:
        """Clear a matching recoverable pause after that stage has succeeded."""
        if self.blocked_stage not in {None, stage}:
            raise EpisodeValidationError(
                f"无法清除 {stage!r} 的暂停；当前暂停阶段是 {self.blocked_stage!r}"
            )
        self._data["blocked"] = False
        self._data["blocked_stage"] = None
        self._data["last_error"] = None
        self._data["updated_at"] = _now_iso()

    def complete_stage(self, stage: str) -> None:
        """标记一个阶段完成（幂等）。"""
        if self.blocked:
            raise EpisodeValidationError("暂停状态不得提交阶段完成")
        stages = self._data.setdefault("completed_stages", [])
        if stage not in stages:
            stages.append(stage)
        self._data["updated_at"] = _now_iso()

    def retain_completed_stages(self, allowed: set[str]) -> None:
        """Keep only successful stages explicitly allowed by a reset target."""
        self._data["completed_stages"] = [
            stage for stage in self.completed_stages if stage in allowed
        ]
        self._data["updated_at"] = _now_iso()

    def migrate_legacy_block(self) -> bool:
        """Normalize a pre-blocked_stage Episode in memory for resumable recovery."""
        if self.status != EpisodeStatus.BLOCKED or self.blocked_stage is not None:
            return False
        stage = next(
            (candidate for candidate in _ACTIVE_STAGE_ORDER if candidate not in self.completed_stages),
            None,
        )
        if stage is None:
            return False
        self._data["status"] = _LEGACY_STAGE_STATUS[stage]
        self._data["blocked"] = True
        self._data["blocked_stage"] = stage
        self._data["updated_at"] = _now_iso()
        return True

    # ── Schema 校验 ───────────────────────────────────────────────────

    def validate_schema(self) -> None:
        """对当前数据执行 JSON Schema 校验；失败时抛出 EpisodeValidationError。"""
        try:
            schema = _load_schema()
            jsonschema.Draft7Validator(
                schema,
                format_checker=jsonschema.FormatChecker(),
            ).validate(self._data)
            if self.mode in self._UNPUBLISHABLE_MODES and self.publishable:
                raise EpisodeValidationError(
                    "REFERENCE_CLONE 必须设置 publishable=false"
                )
            for name, artifact in self.artifacts.items():
                if Path(artifact).is_absolute() or ".." in Path(artifact).parts:
                    raise EpisodeValidationError(f"产物路径必须为 Episode 相对路径: {name}")
        except jsonschema.ValidationError as exc:
            raise EpisodeValidationError(
                f"episode.json Schema 校验失败: {exc.message}"
            ) from exc
        except FileNotFoundError as exc:
            raise EpisodeValidationError(str(exc)) from exc

    # ── 序列化 ────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """返回数据的浅拷贝（防止外部直接修改内部状态）。"""
        return dict(self._data)

    def __repr__(self) -> str:
        return f"EpisodeModel(id={self.id!r}, status={self.status!r}, mode={self.mode!r})"
