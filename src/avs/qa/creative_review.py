"""Creative review orchestration.

Two things are kept strictly apart here.  ``build_review`` measures the film and
assembles a review package but never invents a score; ``record_scores`` accepts
scores from whoever actually watched it.  That split is what lets a Creative
Runtime Agent be the reviewer on a machine with no vision API key, without the
pipeline ever pretending an unscored video passed.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from avs.qa.creative_metrics import compute_metrics, load_timeline, shot_boundaries
from avs.qa.creative_sampling import (
    MIN_SHEET_WIDTH,
    build_contact_sheets,
    build_sample_plan,
    extract_frames,
    extract_uniform_frames,
)

_SCHEMA = Path(__file__).resolve().parents[3] / "schemas" / "creative-review.schema.json"

REVIEW_PATH = ("work", "qa", "creative-review.json")
BASELINE_PATH = ("work", "qa", "creative-baseline.json")

SCORE_WEIGHTS: dict[str, float] = {
    "hook": 0.15,
    "narrative": 0.15,
    "pacing": 0.15,
    "visual_design": 0.15,
    "human_tone": 0.10,
    "audio": 0.10,
    "caption": 0.05,
    "evidence_trust": 0.05,
    "platform_fit": 0.05,
    "memorability": 0.05,
}
CORE_DIMENSIONS = ("hook", "narrative", "pacing", "visual_design", "human_tone", "audio")
OVERALL_THRESHOLD = 8.0
DIMENSION_FLOOR = 7.0
MAX_REPAIR_ROUNDS = 3
UNIFORM_STEP_SECONDS = 0.5

# Deterministic thresholds. Each one is a measurable proxy for a creative defect,
# not a taste judgement — the agent still scores the film itself.
HOOK_STATIC_LIMIT = 1.5
STATIC_RUN_LIMIT = 2.0
SHOT_VARIETY_MIN = 3
# Counting distinct durations alone gives false negatives: 11 shots at
# 3.2/3.6/4.0s clear a distinct-value check while still being a square wave.
# Spread (range / mean) catches tightly clustered durations regardless of count.
SHOT_SPREAD_MIN = 0.6
EVIDENCE_SCALE_FLOOR = 0.55
BLACK_BORDER_LIMIT = 0.05


def _schema() -> dict[str, Any]:
    return json.loads(_SCHEMA.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_video(episode_dir: Path, video_path: Path | None) -> Path:
    if video_path is not None:
        return video_path
    candidates = (
        episode_dir / "renders" / "final-with-captions.mp4",
        episode_dir / "renders" / "preview-with-motion.mp4",
        episode_dir / "renders" / "preview-with-captions.mp4",
    )
    return next((path for path in candidates if path.is_file()), candidates[-1])


def weighted_overall(scores: dict[str, float]) -> float:
    total = sum(
        float(scores[name]) * weight
        for name, weight in SCORE_WEIGHTS.items()
        if name in scores
    )
    return round(total, 2)


def derive_findings(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    """Findings that follow from measurements alone, with a repair target each."""
    findings: list[dict[str, Any]] = []

    hook_static = float(metrics.get("hook_static_seconds", 0.0))
    if hook_static > HOOK_STATIC_LIMIT:
        findings.append({
            "timestamp": 0.0,
            "dimension": "HOOK",
            "severity": "CRITICAL",
            "observation": f"开场 {hook_static:.1f}s 内画面无有效变化",
            "why_it_hurts": "前 3 秒是留存唯一决定点，静态画面等于放弃钩子",
            "repair_target": "storyboard",
            "recommended_action": "把 Hook 拆成 2-3 个 Visual Beat，加入数字动画或 ROI 切换",
            "source": "deterministic",
        })

    distinct = int(metrics.get("shot_duration_distinct_values", 0))
    shot_count = int(metrics.get("shot_count", 0))
    mean_duration = float(metrics.get("shot_duration_mean", 0.0))
    spread = (
        (float(metrics.get("shot_duration_max", 0.0)) - float(metrics.get("shot_duration_min", 0.0)))
        / mean_duration
        if mean_duration > 0
        else 0.0
    )
    if shot_count >= SHOT_VARIETY_MIN and (distinct < SHOT_VARIETY_MIN or spread < SHOT_SPREAD_MIN):
        findings.append({
            "timestamp": 0.0,
            "dimension": "PACING",
            "severity": "HIGH",
            "observation": (
                f"{shot_count} 个镜头只有 {distinct} 种时长，"
                f"极差/均值={spread:.2f}（<{SHOT_SPREAD_MIN} 视为方波）"
            ),
            "why_it_hurts": "等长镜头让节奏变成方波，观众很快预测到下一次切换",
            "repair_target": "edit",
            "recommended_action": "按叙事重要度分配时长，关键点缩短、解释段放长",
            "source": "deterministic",
        })

    longest_static = float(metrics.get("longest_static_run_seconds", 0.0))
    if longest_static > STATIC_RUN_LIMIT:
        findings.append({
            "timestamp": 0.0,
            "dimension": "VISUAL_DESIGN",
            "severity": "HIGH",
            "observation": f"存在 {longest_static:.1f}s 连续静态画面",
            "why_it_hurts": "旁白继续推进但画面无信息增量，形成 PPT 感",
            "repair_target": "storyboard",
            "recommended_action": "拆分为多个 Visual Beat，或加入局部放大、平移、高亮",
            "source": "deterministic",
        })

    for item in metrics.get("evidence_scale_factors", []):
        scale = float(item.get("scale_factor", 0.0))
        if 0.0 < scale < EVIDENCE_SCALE_FLOOR:
            findings.append({
                "timestamp": 0.0,
                "dimension": "EVIDENCE_TRUST",
                "severity": "CRITICAL",
                "observation": (
                    f"{Path(str(item.get('asset_ref'))).name} 缩放至 {scale * 100:.0f}%，"
                    f"清晰带仅占画布 {float(item.get('sharp_band_ratio', 0.0)) * 100:.0f}%"
                ),
                "why_it_hurts": "证据文字缩到不可读时，旁白宣称的证据实际不存在",
                "repair_target": "asset",
                "recommended_action": "改用 ROI 局部裁切放大到可读尺寸，不要整屏塞进竖屏",
                "source": "deterministic",
            })

    if not metrics.get("has_bgm"):
        findings.append({
            "timestamp": 0.0,
            "dimension": "AUDIO",
            "severity": "MEDIUM",
            "observation": "无 BGM 轨",
            "why_it_hurts": "纯人声在竖屏平台显得单薄，缺少能量曲线",
            "repair_target": "audio",
            "recommended_action": "按 Narrative Beat 选择 BGM 并设计能量变化与 ducking",
            "source": "deterministic",
        })

    providers = list(metrics.get("voice_providers", []))
    if len(providers) == 1:
        findings.append({
            "timestamp": 0.0,
            "dimension": "AUDIO",
            "severity": "MEDIUM",
            "observation": f"配音全片单一 provider ({providers[0]}) 且无语气标记",
            "why_it_hurts": "机械 TTS 是最容易被识别的 AI 味来源",
            "repair_target": "audio",
            "recommended_action": "为每个 Beat 指定语速、停顿与重音；关键数字重读",
            "source": "deterministic",
        })

    border = float(metrics.get("max_black_border_ratio", 0.0))
    if border > BLACK_BORDER_LIMIT:
        findings.append({
            "timestamp": 0.0,
            "dimension": "TECHNICAL",
            "severity": "HIGH",
            "observation": f"检出黑边占比 {border * 100:.1f}%",
            "why_it_hurts": "黑边在竖屏平台直接降低完播率与推荐权重",
            "repair_target": "render",
            "recommended_action": "改用 cover / screen_focus 布局消除黑边",
            "source": "deterministic",
        })

    return findings


def evaluate_gate(
    metrics: dict[str, Any],
    scores: dict[str, Any] | None,
    findings: list[dict[str, Any]],
    *,
    repair_round: int = 0,
) -> dict[str, Any]:
    technical_failures = [
        item["observation"] for item in findings if item["dimension"] == "TECHNICAL"
    ]
    if float(metrics.get("duration_seconds", 0.0)) <= 0:
        technical_failures.append("视频不可解码或时长为 0")
    failed_dimensions: list[str] = []
    creative_passed = False
    if scores:
        failed_dimensions = [
            name for name in CORE_DIMENSIONS
            if float(scores.get(name, 0.0)) < DIMENSION_FLOOR
        ]
        creative_passed = (
            float(scores.get("overall", 0.0)) >= OVERALL_THRESHOLD and not failed_dimensions
        )
    technical_passed = not technical_failures
    return {
        "technical_passed": technical_passed,
        "creative_passed": creative_passed,
        "overall_threshold": OVERALL_THRESHOLD,
        "dimension_floor": DIMENSION_FLOOR,
        "failed_dimensions": failed_dimensions,
        "technical_failures": technical_failures,
        "repair_round": repair_round,
        "repair_allowed": not (technical_passed and creative_passed) and repair_round < MAX_REPAIR_ROUNDS,
    }


def build_review(
    episode_dir: Path,
    episode_id: str,
    *,
    video_path: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Measure the film and assemble the review package. Scores stay ``None``."""
    video = _resolve_video(episode_dir, video_path)
    if not video.is_file():
        raise RuntimeError(f"没有可审核的视频: {video}")
    timeline = load_timeline(episode_dir)
    qa_dir = episode_dir / "work" / "qa"
    uniform = extract_uniform_frames(
        video, qa_dir / "uniform-frames", step_seconds=UNIFORM_STEP_SECONDS, force=force,
    )
    metrics = compute_metrics(episode_dir, video, timeline, uniform)
    duration = float(metrics.get("duration_seconds", 0.0))
    plan = build_sample_plan(duration, shot_boundaries(timeline))
    review_frames = extract_frames(
        video, [item["timestamp"] for item in plan], qa_dir / "review-frames", force=force,
    )
    hook_frames = {stamp: path for stamp, path in review_frames.items() if stamp <= 5.0}
    body_frames = {stamp: path for stamp, path in review_frames.items() if stamp > 5.0}
    sheets = build_contact_sheets(hook_frames, qa_dir / "sheets", label="hook")
    sheets.extend(build_contact_sheets(body_frames, qa_dir / "sheets", label="body"))
    findings = derive_findings(metrics)
    baseline = load_baseline(episode_dir)
    review = {
        "episode_id": episode_id,
        "video_path": video.relative_to(episode_dir).as_posix(),
        "video_sha256": _sha256(video),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewer_kind": "pending",
        "reviewer_id": None,
        "reviewed_artifacts": [],
        "baseline_ref": (baseline or {}).get("video_sha256"),
        "metrics": metrics,
        "scores": None,
        "findings": findings,
        "gate": evaluate_gate(metrics, None, findings),
        "review_package": {
            "contact_sheets": sheets,
            "sample_plan": plan,
            "frame_count": len(review_frames),
            "transcript_path": _transcript_path(episode_dir),
            "min_sheet_width": MIN_SHEET_WIDTH,
        },
    }
    jsonschema.Draft7Validator(_schema()).validate(review)
    save_review(episode_dir, review)
    return review


def _transcript_path(episode_dir: Path) -> str | None:
    for relative in ("work/content/script.json", "work/captions.srt"):
        if (episode_dir / relative).is_file():
            return relative
    return None


def record_scores(
    episode_dir: Path,
    scores: dict[str, float],
    *,
    reviewer_kind: str = "agent",
    reviewer_id: str | None = None,
    reviewed_artifacts: list[str] | None = None,
    findings: list[dict[str, Any]] | None = None,
    repair_round: int | None = None,
) -> dict[str, Any]:
    """Attach scores from whoever watched the film, then re-evaluate the gate."""
    review = load_review(episode_dir)
    if review is None:
        raise RuntimeError("请先运行 creative review 生成审片包")
    missing = [name for name in SCORE_WEIGHTS if name not in scores]
    if missing:
        raise ValueError("缺少维度评分: " + ", ".join(sorted(missing)))
    if reviewer_kind not in {"agent", "provider"}:
        raise ValueError("评分审片人必须为 agent 或 provider")
    if not reviewer_id or not reviewer_id.strip():
        raise ValueError("评分审片人必须提供 reviewer_id")
    if not reviewed_artifacts or not all(isinstance(item, str) and item.strip() for item in reviewed_artifacts):
        raise ValueError("评分必须列出至少一个实际查看的 reviewed_artifacts")
    resolved = {name: float(scores[name]) for name in SCORE_WEIGHTS}
    resolved["overall"] = float(scores.get("overall") or weighted_overall(resolved))
    merged = [item for item in review.get("findings", []) if item.get("source") == "deterministic"]
    for item in findings or []:
        merged.append({**item, "source": item.get("source", reviewer_kind)})
    round_index = (
        repair_round
        if repair_round is not None
        else int(review.get("gate", {}).get("repair_round", 0))
    )
    review["scores"] = resolved
    review["findings"] = merged
    review["reviewer_kind"] = reviewer_kind
    review["reviewer_id"] = reviewer_id
    review["reviewed_artifacts"] = list(reviewed_artifacts)
    review["gate"] = evaluate_gate(review["metrics"], resolved, merged, repair_round=round_index)
    review["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    jsonschema.Draft7Validator(_schema()).validate(review)
    save_review(episode_dir, review)
    return review


def save_review(episode_dir: Path, review: dict[str, Any]) -> Path:
    path = episode_dir.joinpath(*REVIEW_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_review(episode_dir: Path) -> dict[str, Any] | None:
    path = episode_dir.joinpath(*REVIEW_PATH)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_baseline(episode_dir: Path) -> dict[str, Any] | None:
    path = episode_dir.joinpath(*BASELINE_PATH)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def promote_baseline(episode_dir: Path) -> Path:
    """Freeze the current review as the comparison baseline."""
    review = load_review(episode_dir)
    if review is None:
        raise RuntimeError("没有可固定为基线的 creative-review.json")
    if review.get("scores") is None:
        raise RuntimeError("基线必须已评分，否则无法作为对比参照")
    path = episode_dir.joinpath(*BASELINE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def compare_to_baseline(episode_dir: Path) -> dict[str, Any]:
    """Baseline vs current, per dimension, with deltas."""
    current = load_review(episode_dir)
    if current is None:
        raise RuntimeError("没有 creative-review.json")
    baseline = load_baseline(episode_dir)
    rows: list[dict[str, Any]] = []
    dimensions = [*SCORE_WEIGHTS, "overall"]
    for name in dimensions:
        base_value = None
        if baseline and baseline.get("scores"):
            base_value = float(baseline["scores"].get(name, 0.0))
        current_value = None
        if current.get("scores"):
            current_value = float(current["scores"].get(name, 0.0))
        delta = (
            round(current_value - base_value, 2)
            if base_value is not None and current_value is not None
            else None
        )
        rows.append({
            "dimension": name,
            "baseline": base_value,
            "current": current_value,
            "delta": delta,
        })
    improved = [row for row in rows if row["delta"] is not None and row["delta"] > 0]
    regressed = [row for row in rows if row["delta"] is not None and row["delta"] < 0]
    return {
        "episode_id": current["episode_id"],
        "baseline_video_sha256": (baseline or {}).get("video_sha256"),
        "current_video_sha256": current["video_sha256"],
        "has_baseline": baseline is not None,
        "rows": rows,
        "improved_count": len(improved),
        "regressed_count": len(regressed),
        "metric_deltas": _metric_deltas(baseline, current),
    }


def _metric_deltas(baseline: dict[str, Any] | None, current: dict[str, Any]) -> list[dict[str, Any]]:
    tracked = (
        "duration_seconds", "shot_count", "shot_duration_distinct_values",
        "longest_static_run_seconds", "hook_static_seconds", "visual_change_rate",
        "max_black_border_ratio",
    )
    deltas: list[dict[str, Any]] = []
    for name in tracked:
        current_value = current.get("metrics", {}).get(name)
        base_value = (baseline or {}).get("metrics", {}).get(name) if baseline else None
        delta = (
            round(float(current_value) - float(base_value), 3)
            if isinstance(current_value, (int, float)) and isinstance(base_value, (int, float))
            else None
        )
        deltas.append({"metric": name, "baseline": base_value, "current": current_value, "delta": delta})
    return deltas
