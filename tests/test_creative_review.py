"""Creative review harness tests.

The point of these tests is the contract, not taste: sampling must actually
cover hook and cuts, metrics must be derived from pixels/timeline rather than
assumed, and an unscored review must never be able to pass the gate.
"""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from PIL import Image

from avs.qa.creative_review import (
    DIMENSION_FLOOR,
    OVERALL_THRESHOLD,
    SCORE_WEIGHTS,
    build_review,
    compare_to_baseline,
    derive_findings,
    evaluate_gate,
    load_review,
    promote_baseline,
    record_scores,
    weighted_overall,
)
from avs.qa.creative_sampling import build_contact_sheets, build_sample_plan

SCHEMA = json.loads(
    (Path(__file__).parents[1] / "schemas" / "creative-review.schema.json").read_text(encoding="utf-8")
)


def _passing_scores() -> dict[str, float]:
    return {name: 8.5 for name in SCORE_WEIGHTS}


# ── sampling ──────────────────────────────────────────────────────────


def test_sample_plan_densifies_hook_window() -> None:
    plan = build_sample_plan(40.0, [4.0, 8.0])
    hook = [item for item in plan if item["timestamp"] < 5.0]
    assert len(hook) >= 8, "开场 5 秒必须高密度采样"
    # Uniform fps=1 would give 5 samples in the hook window; we need finer.
    assert any(item["reason"] == "hook_dense" for item in hook)


def test_sample_plan_brackets_every_shot_boundary() -> None:
    plan = build_sample_plan(40.0, [12.0])
    stamps = [item["timestamp"] for item in plan]
    assert any(abs(value - 11.75) < 0.01 for value in stamps), "切换前"
    assert 12.0 in stamps, "切换瞬间"
    assert any(abs(value - 12.35) < 0.01 for value in stamps), "切换后"


def test_sample_plan_never_exceeds_duration() -> None:
    plan = build_sample_plan(3.0, [1.0, 2.0])
    assert plan
    assert all(item["timestamp"] < 3.0 for item in plan)


def test_sample_plan_empty_for_zero_duration() -> None:
    assert build_sample_plan(0.0, []) == []


def test_hook_reason_survives_interval_collision() -> None:
    # 0.0 is both a hook sample and an interval candidate; hook intent must win.
    plan = build_sample_plan(20.0, [])
    first = next(item for item in plan if item["timestamp"] == 0.0)
    assert first["reason"] == "hook_dense"


def test_contact_sheet_meets_min_width(tmp_path: Path) -> None:
    frames: dict[float, Path] = {}
    for index in range(4):
        path = tmp_path / f"frame-{index}.png"
        Image.new("RGB", (1080, 1920), (index * 40, 10, 10)).save(path)
        frames[float(index)] = path
    sheets = build_contact_sheets(frames, tmp_path / "sheets", label="t")
    assert sheets
    for sheet in sheets:
        # Narrow sheets are dropped by some agent transports; the package would
        # look complete while carrying no pixels.
        assert sheet["width"] >= 2560


def test_contact_sheet_empty_input(tmp_path: Path) -> None:
    assert build_contact_sheets({}, tmp_path / "sheets") == []


# ── deterministic findings ────────────────────────────────────────────


def test_static_hook_is_critical_finding() -> None:
    findings = derive_findings({
        "hook_static_seconds": 4.0, "shot_count": 11,
        "shot_duration_distinct_values": 2, "longest_static_run_seconds": 3.5,
        "shot_duration_min": 3.6, "shot_duration_max": 4.0, "shot_duration_mean": 3.8,
        "evidence_scale_factors": [], "has_bgm": True, "voice_providers": ["a", "b"],
        "max_black_border_ratio": 0.0,
    })
    hook = [item for item in findings if item["dimension"] == "HOOK"]
    assert hook and hook[0]["severity"] == "CRITICAL"
    assert hook[0]["repair_target"] == "storyboard"


def test_square_wave_pacing_detected() -> None:
    findings = derive_findings({
        "hook_static_seconds": 0.0, "shot_count": 11,
        "shot_duration_distinct_values": 2, "longest_static_run_seconds": 0.0,
        "shot_duration_min": 3.6, "shot_duration_max": 4.0, "shot_duration_mean": 3.8,
        "evidence_scale_factors": [], "has_bgm": True, "voice_providers": ["a", "b"],
        "max_black_border_ratio": 0.0,
    })
    assert any(item["dimension"] == "PACING" for item in findings)


def test_clustered_durations_detected_despite_enough_distinct_values() -> None:
    """Regression: the real benchmark had 3 distinct durations spanning 0.8s.

    A distinct-value check alone cleared it, so the flattest pacing in the
    baseline film produced no finding at all. Spread is what actually matters.
    """
    findings = derive_findings({
        "hook_static_seconds": 0.0, "shot_count": 11,
        "shot_duration_distinct_values": 3, "longest_static_run_seconds": 0.0,
        "shot_duration_min": 3.2, "shot_duration_max": 4.0, "shot_duration_mean": 3.673,
        "evidence_scale_factors": [], "has_bgm": True, "voice_providers": ["a", "b"],
        "max_black_border_ratio": 0.0,
    })
    pacing = [item for item in findings if item["dimension"] == "PACING"]
    assert pacing, "极差 0.8s / 均值 3.67 = 0.22，必须判为方波"
    assert "极差/均值" in pacing[0]["observation"]


def test_unreadable_evidence_is_critical() -> None:
    findings = derive_findings({
        "hook_static_seconds": 0.0, "shot_count": 3,
        "shot_duration_distinct_values": 3, "longest_static_run_seconds": 0.0,
        "shot_duration_min": 1.2, "shot_duration_max": 4.0, "shot_duration_mean": 2.6,
        "evidence_scale_factors": [
            {"asset_ref": "work/prepared/shot.png", "scale_factor": 0.42, "sharp_band_ratio": 0.28},
        ],
        "has_bgm": True, "voice_providers": ["a", "b"], "max_black_border_ratio": 0.0,
    })
    evidence = [item for item in findings if item["dimension"] == "EVIDENCE_TRUST"]
    assert evidence and evidence[0]["severity"] == "CRITICAL"
    assert evidence[0]["repair_target"] == "asset"


def test_healthy_metrics_produce_no_findings() -> None:
    assert derive_findings({
        "hook_static_seconds": 0.5, "shot_count": 12,
        "shot_duration_distinct_values": 7, "longest_static_run_seconds": 1.0,
        "shot_duration_min": 0.8, "shot_duration_max": 4.2, "shot_duration_mean": 2.4,
        "evidence_scale_factors": [
            {"asset_ref": "a.png", "scale_factor": 0.9, "sharp_band_ratio": 0.7},
        ],
        "has_bgm": True, "voice_providers": ["edge", "azure"],
        "max_black_border_ratio": 0.0,
    }) == []


# ── gate ──────────────────────────────────────────────────────────────


def test_gate_blocks_when_scores_absent() -> None:
    gate = evaluate_gate({"duration_seconds": 40.0}, None, [])
    assert gate["technical_passed"] is True
    assert gate["creative_passed"] is False, "未评分不得过创作闸门"


def test_gate_blocks_low_core_dimension() -> None:
    scores = _passing_scores()
    scores["pacing"] = DIMENSION_FLOOR - 0.5
    scores["overall"] = OVERALL_THRESHOLD + 0.5
    gate = evaluate_gate({"duration_seconds": 40.0}, scores, [])
    assert gate["creative_passed"] is False
    assert "pacing" in gate["failed_dimensions"]


def test_gate_passes_when_all_thresholds_met() -> None:
    scores = _passing_scores()
    scores["overall"] = weighted_overall(scores)
    gate = evaluate_gate({"duration_seconds": 40.0}, scores, [])
    assert gate["creative_passed"] is True
    assert gate["repair_allowed"] is False


def test_gate_fails_technical_on_undecodable_video() -> None:
    gate = evaluate_gate({"duration_seconds": 0.0}, _passing_scores(), [])
    assert gate["technical_passed"] is False


def test_repair_stops_after_max_rounds() -> None:
    scores = _passing_scores()
    scores["hook"] = 4.0
    scores["overall"] = weighted_overall(scores)
    assert evaluate_gate({"duration_seconds": 40.0}, scores, [], repair_round=3)["repair_allowed"] is False
    assert evaluate_gate({"duration_seconds": 40.0}, scores, [], repair_round=1)["repair_allowed"] is True


def test_weighted_overall_uses_spec_weights() -> None:
    assert weighted_overall({name: 10.0 for name in SCORE_WEIGHTS}) == pytest.approx(10.0)
    assert sum(SCORE_WEIGHTS.values()) == pytest.approx(1.0)


# ── end to end on a synthetic episode ─────────────────────────────────


def _episode(tmp_path: Path, *, frames: int = 12) -> Path:
    episode = tmp_path / "EP-CREATIVE-TEST"
    (episode / "renders").mkdir(parents=True)
    (episode / "work" / "qa" / "uniform-frames").mkdir(parents=True)
    (episode / "work" / "prepared").mkdir(parents=True)
    Image.new("RGB", (2560, 1271), (200, 200, 200)).save(episode / "work" / "prepared" / "wide.png")
    (episode / "renders" / "preview-with-motion.mp4").write_bytes(b"fake-mp4")
    timeline = {
        "tracks": [
            {"kind": "video", "clips": [
                {"clip_id": "v1", "start": 0.0, "duration": 4.0, "asset_ref": None},
                {"clip_id": "v2", "start": 4.0, "duration": 4.0, "asset_ref": "work/prepared/wide.png"},
                {"clip_id": "v3", "start": 8.0, "duration": 4.0, "asset_ref": "work/prepared/wide.png"},
            ]},
            {"kind": "audio", "audio_role": "voice", "clips": [
                {"clip_id": "a1", "start": 0.0, "duration": 12.0,
                 "style": {"role": "voice", "provider": "edge_tts"}},
            ]},
        ],
    }
    (episode / "work" / "timeline.json").write_text(json.dumps(timeline), encoding="utf-8")
    for index in range(frames):
        Image.new("RGB", (1080, 1920), (60, 60, 60)).save(
            episode / "work" / "qa" / "uniform-frames" / f"u-{index:04d}.png"
        )
    return episode


def test_build_review_validates_and_leaves_scores_null(tmp_path: Path, monkeypatch) -> None:
    episode = _episode(tmp_path)
    monkeypatch.setattr("avs.qa.creative_metrics.probe_duration", lambda _: 12.0)
    monkeypatch.setattr(
        "avs.qa.creative_review.extract_frames",
        lambda *args, **kwargs: {
            stamp: episode / "work" / "qa" / "uniform-frames" / "u-0000.png"
            for stamp in (0.0, 1.0, 4.0, 8.0)
        },
    )
    review = build_review(episode, "EP-CREATIVE-TEST")
    jsonschema.Draft7Validator(SCHEMA).validate(review)
    assert review["scores"] is None
    assert review["reviewer_kind"] == "pending"
    assert review["gate"]["creative_passed"] is False
    # Landscape source on a vertical canvas: readability collapses to ~42%.
    factors = review["metrics"]["evidence_scale_factors"]
    assert factors and factors[0]["scale_factor"] == pytest.approx(1080 / 2560, abs=1e-3)
    assert any(item["dimension"] == "EVIDENCE_TRUST" for item in review["findings"])


def test_all_identical_frames_report_static_run(tmp_path: Path, monkeypatch) -> None:
    episode = _episode(tmp_path)
    monkeypatch.setattr("avs.qa.creative_metrics.probe_duration", lambda _: 6.0)
    monkeypatch.setattr("avs.qa.creative_review.extract_frames", lambda *a, **k: {})
    review = build_review(episode, "EP-CREATIVE-TEST")
    assert review["metrics"]["longest_static_run_seconds"] > 2.0
    assert review["metrics"]["static_frame_ratio"] == pytest.approx(1.0)


def test_score_then_baseline_then_compare(tmp_path: Path, monkeypatch) -> None:
    episode = _episode(tmp_path)
    monkeypatch.setattr("avs.qa.creative_metrics.probe_duration", lambda _: 12.0)
    monkeypatch.setattr("avs.qa.creative_review.extract_frames", lambda *a, **k: {})
    build_review(episode, "EP-CREATIVE-TEST")

    weak = {name: 4.0 for name in SCORE_WEIGHTS}
    record_scores(episode, weak, reviewer_id="test-agent")
    promote_baseline(episode)

    strong = {name: 8.5 for name in SCORE_WEIGHTS}
    record_scores(episode, strong, reviewer_id="test-agent")
    comparison = compare_to_baseline(episode)
    assert comparison["has_baseline"] is True
    overall = next(row for row in comparison["rows"] if row["dimension"] == "overall")
    assert overall["baseline"] == pytest.approx(4.0)
    assert overall["current"] == pytest.approx(8.5)
    assert overall["delta"] == pytest.approx(4.5)
    assert comparison["regressed_count"] == 0


def test_record_scores_rejects_partial_dimensions(tmp_path: Path, monkeypatch) -> None:
    episode = _episode(tmp_path)
    monkeypatch.setattr("avs.qa.creative_metrics.probe_duration", lambda _: 12.0)
    monkeypatch.setattr("avs.qa.creative_review.extract_frames", lambda *a, **k: {})
    build_review(episode, "EP-CREATIVE-TEST")
    with pytest.raises(ValueError, match="缺少维度评分"):
        record_scores(episode, {"hook": 9.0})


def test_baseline_requires_scores(tmp_path: Path, monkeypatch) -> None:
    episode = _episode(tmp_path)
    monkeypatch.setattr("avs.qa.creative_metrics.probe_duration", lambda _: 12.0)
    monkeypatch.setattr("avs.qa.creative_review.extract_frames", lambda *a, **k: {})
    build_review(episode, "EP-CREATIVE-TEST")
    with pytest.raises(RuntimeError, match="必须已评分"):
        promote_baseline(episode)


def test_score_without_review_fails(tmp_path: Path) -> None:
    episode = tmp_path / "EP-EMPTY"
    episode.mkdir()
    with pytest.raises(RuntimeError, match="请先运行"):
        record_scores(episode, {name: 8.0 for name in SCORE_WEIGHTS})


def test_agent_findings_merge_with_deterministic(tmp_path: Path, monkeypatch) -> None:
    episode = _episode(tmp_path)
    monkeypatch.setattr("avs.qa.creative_metrics.probe_duration", lambda _: 12.0)
    monkeypatch.setattr("avs.qa.creative_review.extract_frames", lambda *a, **k: {})
    build_review(episode, "EP-CREATIVE-TEST")
    review = record_scores(
        episode,
        {name: 6.0 for name in SCORE_WEIGHTS},
        findings=[{
            "timestamp": 2.5, "dimension": "HOOK", "severity": "HIGH",
            "observation": "开场文字卡无视觉锚点", "why_it_hurts": "观众没有停下来的理由",
            "repair_target": "hook", "recommended_action": "用真实数字或反差画面开场",
        }],
        reviewer_id="claude",
    )
    jsonschema.Draft7Validator(SCHEMA).validate(review)
    sources = {item.get("source") for item in review["findings"]}
    assert "deterministic" in sources and "agent" in sources
    assert load_review(episode)["reviewer_id"] == "claude"


def test_rescoring_replaces_previous_agent_findings(tmp_path: Path, monkeypatch) -> None:
    episode = _episode(tmp_path)
    monkeypatch.setattr("avs.qa.creative_metrics.probe_duration", lambda _: 12.0)
    monkeypatch.setattr("avs.qa.creative_review.extract_frames", lambda *a, **k: {})
    build_review(episode, "EP-CREATIVE-TEST")
    finding = {
        "timestamp": 1.0, "dimension": "PACING", "severity": "HIGH",
        "observation": "第一轮观察", "why_it_hurts": "节奏平",
        "repair_target": "edit", "recommended_action": "调整时长",
    }
    record_scores(episode, {name: 5.0 for name in SCORE_WEIGHTS}, findings=[finding])
    second = record_scores(episode, {name: 7.0 for name in SCORE_WEIGHTS}, findings=[])
    agent_findings = [item for item in second["findings"] if item.get("source") == "agent"]
    assert agent_findings == [], "重新评分必须清掉上一轮主观发现，避免陈旧结论累积"
