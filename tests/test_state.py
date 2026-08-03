"""tests/test_state.py — 状态机单元测试。"""
from __future__ import annotations

import pytest

from avs.state import (
    EpisodeStatus,
    TransitionError,
    all_states,
    assert_transition,
    can_transition,
)


class TestValidTransitions:
    """合法状态转换。"""

    def test_created_to_ingested(self):
        assert can_transition(EpisodeStatus.CREATED, EpisodeStatus.INGESTED)

    def test_ingested_to_reference_ready(self):
        assert can_transition(EpisodeStatus.INGESTED, EpisodeStatus.REFERENCE_READY)

    def test_ingested_to_content_ready_skip_reference(self):
        """无参考视频时允许跳过 REFERENCE_READY。"""
        assert can_transition(EpisodeStatus.INGESTED, EpisodeStatus.CONTENT_READY)

    def test_reference_ready_to_content_ready(self):
        assert can_transition(EpisodeStatus.REFERENCE_READY, EpisodeStatus.CONTENT_READY)

    def test_full_pipeline(self):
        """完整流水线顺序转换全部合法。"""
        pipeline = [
            EpisodeStatus.CREATED,
            EpisodeStatus.INGESTED,
            EpisodeStatus.REFERENCE_READY,
            EpisodeStatus.CONTENT_READY,
            EpisodeStatus.ASSETS_READY,
            EpisodeStatus.TIMELINE_READY,
            EpisodeStatus.ROUGH_CUT_READY,
            EpisodeStatus.QA_PASSED,
            EpisodeStatus.DELIVERY_READY,
        ]
        for i in range(len(pipeline) - 1):
            assert can_transition(pipeline[i], pipeline[i + 1]), (
                f"期望合法转换: {pipeline[i]} → {pipeline[i+1]}"
            )

    def test_any_state_to_failed(self):
        """大多数状态可以直接转换到 FAILED。"""
        states_with_fail = [
            EpisodeStatus.CREATED,
            EpisodeStatus.INGESTED,
            EpisodeStatus.REFERENCE_READY,
            EpisodeStatus.CONTENT_READY,
            EpisodeStatus.ASSETS_READY,
            EpisodeStatus.TIMELINE_READY,
            EpisodeStatus.ROUGH_CUT_READY,
            EpisodeStatus.QA_PASSED,
        ]
        for s in states_with_fail:
            assert can_transition(s, EpisodeStatus.FAILED), f"{s} 应允许转换到 FAILED"

    def test_waiting_for_input_to_ingested(self):
        assert can_transition(EpisodeStatus.WAITING_FOR_INPUT, EpisodeStatus.INGESTED)


class TestInvalidTransitions:
    """非法状态转换。"""

    def test_delivery_ready_is_terminal(self):
        """DELIVERY_READY 是终态，不允许任何普通转换。"""
        for target in EpisodeStatus:
            if target != EpisodeStatus.DELIVERY_READY:
                assert not can_transition(
                    EpisodeStatus.DELIVERY_READY, target
                ), f"DELIVERY_READY 不应转换到 {target}"

    def test_skip_ingested(self):
        """不允许 CREATED 直接跳到 CONTENT_READY（必须经过 INGESTED）。"""
        assert not can_transition(EpisodeStatus.CREATED, EpisodeStatus.CONTENT_READY)

    def test_backward_transition(self):
        """不允许后退（INGESTED → CREATED）。"""
        assert not can_transition(EpisodeStatus.INGESTED, EpisodeStatus.CREATED)

    def test_random_jump(self):
        """不允许跨多个状态跳跃。"""
        assert not can_transition(EpisodeStatus.CREATED, EpisodeStatus.DELIVERY_READY)

    def test_assert_raises_on_illegal(self):
        with pytest.raises(TransitionError):
            assert_transition(EpisodeStatus.CREATED, EpisodeStatus.DELIVERY_READY)


class TestForceReset:
    """--force 重置白名单。"""

    def test_failed_force_reset_to_created(self):
        assert can_transition(EpisodeStatus.FAILED, EpisodeStatus.CREATED, force=True)

    def test_delivery_ready_force_reset_to_created(self):
        """DELIVERY_READY 通过 --force 允许重置到 CREATED。"""
        assert can_transition(EpisodeStatus.DELIVERY_READY, EpisodeStatus.CREATED, force=True)

    def test_force_not_bypass_non_whitelist(self):
        """--force 不允许跳到不在白名单的目标（如 DELIVERY_READY）。"""
        assert not can_transition(
            EpisodeStatus.CREATED, EpisodeStatus.DELIVERY_READY, force=True
        )


class TestAllStates:
    def test_all_states_returns_13(self):
        states = all_states()
        assert len(states) == 13, f"期望13个状态，实际 {len(states)}: {states}"

    def test_contains_required(self):
        states = set(all_states())
        required = {
            "CREATED", "INGESTED", "REFERENCE_READY", "CONTENT_READY",
            "ASSETS_READY", "TIMELINE_READY", "ROUGH_CUT_READY",
            "QA_PASSED", "DELIVERY_READY",
            "WAITING_FOR_INPUT", "WAITING_FOR_REVIEW", "BLOCKED", "FAILED",
        }
        assert required == states
