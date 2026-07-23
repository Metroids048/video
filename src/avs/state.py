"""src/avs/state.py — Episode 状态机。

合法转换表硬编码在此；通过 Config 可覆盖（测试友好）。
"""
from __future__ import annotations

from enum import Enum


class EpisodeStatus(str, Enum):
    """Episode 正式状态 + 辅助状态。"""

    # ── 正式流水线状态 ────────────────────────────────────────────────
    CREATED = "CREATED"
    INGESTED = "INGESTED"
    REFERENCE_READY = "REFERENCE_READY"
    CONTENT_READY = "CONTENT_READY"
    ASSETS_READY = "ASSETS_READY"
    TIMELINE_READY = "TIMELINE_READY"
    ROUGH_CUT_READY = "ROUGH_CUT_READY"
    QA_PASSED = "QA_PASSED"
    DELIVERY_READY = "DELIVERY_READY"

    # ── 辅助状态 ──────────────────────────────────────────────────────
    WAITING_FOR_INPUT = "WAITING_FOR_INPUT"
    WAITING_FOR_REVIEW = "WAITING_FOR_REVIEW"
    FAILED = "FAILED"


# 默认合法转换表（来自 AGENTS.md §7 和 config/workflow.yaml 保持一致）
# key = 当前状态；value = 允许转换到的状态集合
_DEFAULT_TRANSITIONS: dict[str, frozenset[str]] = {
    EpisodeStatus.CREATED: frozenset({
        EpisodeStatus.INGESTED,
        EpisodeStatus.WAITING_FOR_INPUT,
        EpisodeStatus.FAILED,
    }),
    EpisodeStatus.INGESTED: frozenset({
        EpisodeStatus.REFERENCE_READY,
        EpisodeStatus.CONTENT_READY,  # 无参考视频时跳过
        EpisodeStatus.WAITING_FOR_INPUT,
        EpisodeStatus.FAILED,
    }),
    EpisodeStatus.REFERENCE_READY: frozenset({
        EpisodeStatus.CONTENT_READY,
        EpisodeStatus.WAITING_FOR_REVIEW,
        EpisodeStatus.FAILED,
    }),
    EpisodeStatus.CONTENT_READY: frozenset({
        EpisodeStatus.ASSETS_READY,
        EpisodeStatus.WAITING_FOR_REVIEW,
        EpisodeStatus.FAILED,
    }),
    EpisodeStatus.ASSETS_READY: frozenset({
        EpisodeStatus.TIMELINE_READY,
        EpisodeStatus.WAITING_FOR_INPUT,
        EpisodeStatus.FAILED,
    }),
    EpisodeStatus.TIMELINE_READY: frozenset({
        EpisodeStatus.ROUGH_CUT_READY,
        EpisodeStatus.FAILED,
    }),
    EpisodeStatus.ROUGH_CUT_READY: frozenset({
        EpisodeStatus.QA_PASSED,
        EpisodeStatus.WAITING_FOR_REVIEW,
        EpisodeStatus.FAILED,
    }),
    EpisodeStatus.QA_PASSED: frozenset({
        EpisodeStatus.DELIVERY_READY,
        EpisodeStatus.FAILED,
    }),
    EpisodeStatus.DELIVERY_READY: frozenset(),  # 终态
    EpisodeStatus.WAITING_FOR_INPUT: frozenset({
        EpisodeStatus.INGESTED,
        EpisodeStatus.CREATED,
        EpisodeStatus.FAILED,
    }),
    EpisodeStatus.WAITING_FOR_REVIEW: frozenset({
        EpisodeStatus.CONTENT_READY,
        EpisodeStatus.ASSETS_READY,
        EpisodeStatus.QA_PASSED,
        EpisodeStatus.FAILED,
    }),
    EpisodeStatus.FAILED: frozenset({
        EpisodeStatus.CREATED,  # 通过 reset --force 重试
    }),
}

# --force reset 允许强制跳到的目标状态白名单
_FORCE_RESET_TARGETS: frozenset[str] = frozenset({
    EpisodeStatus.CREATED,
    EpisodeStatus.INGESTED,
    EpisodeStatus.CONTENT_READY,
})


class TransitionError(Exception):
    """非法状态转换。"""


def can_transition(
    current: str,
    target: str,
    *,
    force: bool = False,
    transitions: dict[str, frozenset[str]] | None = None,
) -> bool:
    """检查是否允许从 current 转换到 target。

    force=True 时还允许白名单内的强制重置目标。
    返回 True/False（不抛异常）。
    """
    table = transitions if transitions is not None else _DEFAULT_TRANSITIONS
    allowed = table.get(current, frozenset())
    if target in allowed:
        return True
    if force and target in _FORCE_RESET_TARGETS:
        return True
    return False


def assert_transition(
    current: str,
    target: str,
    *,
    force: bool = False,
    transitions: dict[str, frozenset[str]] | None = None,
) -> None:
    """与 can_transition 相同，但失败时抛出 TransitionError。"""
    if not can_transition(current, target, force=force, transitions=transitions):
        raise TransitionError(
            f"非法状态转换: {current!r} → {target!r}"
            + (" (尝试 --force 但目标不在白名单)" if force else "")
        )


def all_states() -> list[str]:
    """返回所有已知状态的名称列表（按声明顺序）。"""
    return [s.value for s in EpisodeStatus]
