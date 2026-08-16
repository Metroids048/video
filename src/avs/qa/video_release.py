"""Fail-closed pre-delivery review for the exact rendered video artifact.

Release quality is proven in two directions:
1) source -> final fidelity (frame/context/action preservation), and
2) final -> viewer comprehension (full 1x playback, mobile and audio review).

Sparse frames, metadata, self-scores, or a stable-but-cropped render cannot unlock delivery.
The validated record is content-addressed to both the final MP4 and every declared source
artifact, so either a rerender or source change invalidates the prior pass.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema


REVIEW_INPUT_RELATIVE = Path("work/qa/video-release-review.input.json")
REVIEW_OUTPUT_RELATIVE = Path("work/qa/video-release-review.json")

REQUIRED_TRUE_FLAGS = frozenset({
    "watched_start_to_end_1x",
    "first_pass_without_pause_for_comprehension",
    "first_10s_dense_review_completed",
    "key_evidence_readable_without_pause",
    "audio_listened_end_to_end",
    "mobile_360x640_reviewed",
    "transition_scan_completed",
})

REQUIRED_FALSE_FLAGS = frozenset({
    "slideshow_like",
    "static_screenshot_motion_dominant",
    "rapid_dark_light_switching",
    "unmotivated_abrupt_cuts",
    "abrupt_context_loss",
    "visual_motion_without_semantic_reason",
    "audio_visual_semantic_mismatch",
    "caption_or_overlay_blocks_evidence",
    "key_evidence_requires_pause",
    "known_critical_issue_at_delivery",
})

REQUIRED_SOURCE_TRUE_FLAGS = frozenset({
    "compared_source_to_final",
    "full_frame_integrity_checked",
    "spatial_continuity_checked",
    "temporal_continuity_checked",
    "opening_context_checked",
    "all_crop_events_explicitly_authorized",
})

REQUIRED_SOURCE_FALSE_FLAGS = frozenset({
    "unauthorized_destructive_crop_detected",
    "source_context_loss_detected",
    "spatial_continuity_broken",
    "temporal_continuity_broken",
    "opening_mid_action_or_partial_frame",
})


class VideoReleaseReviewError(ValueError):
    """The current rendered video has not satisfied the release gate."""


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def _project_root(ep_dir: Path) -> Path:
    for candidate in (ep_dir, *ep_dir.parents):
        if (candidate / "schemas" / "video-release-review.schema.json").is_file():
            return candidate
    raise FileNotFoundError("无法定位 schemas/video-release-review.schema.json")


def _resolve_inside_episode(ep_dir: Path, raw: str) -> Path:
    path = (ep_dir / raw).resolve()
    try:
        path.relative_to(ep_dir.resolve())
    except ValueError as exc:
        raise VideoReleaseReviewError(f"review artifact 路径逃逸 Episode: {raw}") from exc
    return path


def _validate_schema(ep_dir: Path, payload: dict[str, Any]) -> None:
    schema_path = _project_root(ep_dir) / "schemas" / "video-release-review.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(
        schema, format_checker=jsonschema.FormatChecker(),
    ).validate(payload)


def _require_nonempty_text(payload: dict[str, Any], key: str) -> None:
    if not str(payload.get(key) or "").strip():
        raise VideoReleaseReviewError(f"{key} 不能为空；必须记录真实观看结果")


def _validate_finding_list(payload: dict[str, Any], key: str) -> None:
    value = payload.get(key)
    if not isinstance(value, list):
        raise VideoReleaseReviewError(f"{key} 必须是 list")
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise VideoReleaseReviewError(f"{key}[{index}] 必须是 object")


def _validate_source_artifacts(ep_dir: Path, source_review: dict[str, Any]) -> None:
    artifacts = source_review.get("source_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise VideoReleaseReviewError(
            "source_fidelity_review.source_artifacts 至少需要一个真实源素材 path + SHA256"
        )

    for index, item in enumerate(artifacts):
        if not isinstance(item, dict):
            raise VideoReleaseReviewError(f"source_artifacts[{index}] 必须是 object")
        raw_path = item.get("path")
        expected_sha = item.get("sha256")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise VideoReleaseReviewError(f"source_artifacts[{index}].path is required")
        if not isinstance(expected_sha, str) or len(expected_sha) != 64:
            raise VideoReleaseReviewError(f"source_artifacts[{index}].sha256 is required")
        source_path = _resolve_inside_episode(ep_dir, raw_path)
        if not source_path.is_file():
            raise VideoReleaseReviewError(f"源素材不存在: {raw_path}")
        current_sha = sha256_file(source_path)
        if current_sha != expected_sha:
            raise VideoReleaseReviewError(
                f"源素材 SHA256 已变化/记录失效: {raw_path}; 必须重新做 source-to-final 验收"
            )


def _validate_source_ready(source_review: dict[str, Any]) -> None:
    missing_true = sorted(
        key for key in REQUIRED_SOURCE_TRUE_FLAGS if source_review.get(key) is not True
    )
    if missing_true:
        raise VideoReleaseReviewError(f"source fidelity 确认项未通过: {missing_true}")

    active_hard_fails = sorted(
        key for key in REQUIRED_SOURCE_FALSE_FLAGS if source_review.get(key) is not False
    )
    if active_hard_fails:
        raise VideoReleaseReviewError(
            f"source fidelity 仍存在 crop/context/连续性 hard fail: {active_hard_fails}"
        )

    findings = source_review.get("source_fidelity_findings")
    if not isinstance(findings, list):
        raise VideoReleaseReviewError("source_fidelity_findings 必须是 list")
    if findings:
        raise VideoReleaseReviewError(
            f"source fidelity 仍存在关键问题，禁止交付: {findings}"
        )


def _validate_ready_to_publish(review: dict[str, Any]) -> None:
    missing_true = sorted(key for key in REQUIRED_TRUE_FLAGS if review.get(key) is not True)
    if missing_true:
        raise VideoReleaseReviewError(f"连续观看确认项未通过: {missing_true}")

    active_hard_fails = sorted(key for key in REQUIRED_FALSE_FLAGS if review.get(key) is not False)
    if active_hard_fails:
        raise VideoReleaseReviewError(f"仍存在发布级 hard fail: {active_hard_fails}")

    critical = review.get("critical_findings")
    if not isinstance(critical, list):
        raise VideoReleaseReviewError("continuous_playback_review.critical_findings 必须是 list")
    if critical:
        raise VideoReleaseReviewError(f"仍存在关键观看问题，禁止交付: {critical}")


def validate_video_release_review(
    ep_dir: Path,
    payload: dict[str, Any],
    *,
    expected_video: Path | None = None,
) -> dict[str, Any]:
    """Validate reviewer input and bind it to the exact current MP4 and sources."""
    ep_dir = ep_dir.resolve()
    reviewer = payload.get("reviewer")
    if not isinstance(reviewer, dict):
        raise VideoReleaseReviewError("reviewer provenance is required")
    if reviewer.get("mode") != "actual_artifact_review":
        raise VideoReleaseReviewError("reviewer.mode 必须为 actual_artifact_review")
    if reviewer.get("inspected_pixels") is not True:
        raise VideoReleaseReviewError("reviewer 必须确认实际检查最终成片像素")
    if reviewer.get("listened_audio") is not True:
        raise VideoReleaseReviewError("reviewer 必须确认实际听完最终音轨")
    if not str(reviewer.get("reviewer_id") or "").strip():
        raise VideoReleaseReviewError("reviewer_id is required")

    reviewed_video = payload.get("reviewed_video")
    if not isinstance(reviewed_video, str) or not reviewed_video.strip():
        raise VideoReleaseReviewError("reviewed_video is required")
    video_path = _resolve_inside_episode(ep_dir, reviewed_video)
    if not video_path.is_file():
        raise VideoReleaseReviewError(f"reviewed_video 不存在: {reviewed_video}")
    if video_path.suffix.lower() != ".mp4":
        raise VideoReleaseReviewError("发布验收必须绑定实际 MP4 成片")

    if expected_video is not None and video_path != expected_video.resolve():
        raise VideoReleaseReviewError(
            "release review 审看的不是当前交付视频；必须重新完整验收当前 MP4"
        )

    source_review = payload.get("source_fidelity_review")
    if not isinstance(source_review, dict):
        raise VideoReleaseReviewError(
            "source_fidelity_review is required; 必须先比较真实源素材与最终成片，不能只看 final"
        )
    _validate_source_artifacts(ep_dir, source_review)

    continuous = payload.get("continuous_playback_review")
    if not isinstance(continuous, dict):
        raise VideoReleaseReviewError(
            "continuous_playback_review is required; 抽帧/contact sheet/metadata 不能替代完整 1x 观看"
        )

    _require_nonempty_text(payload, "first_pass_memory_summary")
    _require_nonempty_text(payload, "audio_review_notes")
    _require_nonempty_text(payload, "mobile_review_notes")
    for key in ("first_10s_findings", "transition_findings", "timestamped_findings"):
        _validate_finding_list(payload, key)

    repair_round = payload.get("repair_round")
    if not isinstance(repair_round, int) or not 0 <= repair_round <= 3:
        raise VideoReleaseReviewError("repair_round 必须为 0..3")

    final_status = payload.get("final_status")
    if final_status not in {"REPAIRING", "BLOCKED", "READY_TO_PUBLISH"}:
        raise VideoReleaseReviewError("final_status 必须为 REPAIRING/BLOCKED/READY_TO_PUBLISH")
    if final_status == "READY_TO_PUBLISH":
        _validate_source_ready(source_review)
        _validate_ready_to_publish(continuous)

    output = dict(payload)
    output["episode_id"] = ep_dir.name
    output["reviewed_video"] = video_path.relative_to(ep_dir).as_posix()
    output["video_sha256"] = sha256_file(video_path)
    output["generated_at"] = datetime.now(timezone.utc).isoformat()
    _validate_schema(ep_dir, output)
    return output


def save_video_release_review(
    ep_dir: Path,
    payload: dict[str, Any],
    *,
    expected_video: Path | None = None,
) -> Path:
    validated = validate_video_release_review(ep_dir, payload, expected_video=expected_video)
    target = ep_dir / REVIEW_OUTPUT_RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(validated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def load_video_release_review(ep_dir: Path) -> dict[str, Any] | None:
    path = ep_dir / REVIEW_OUTPUT_RELATIVE
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        _validate_schema(ep_dir, payload)
        return payload
    except Exception:
        return None


def verify_video_release_review_current(
    ep_dir: Path,
    final_video: Path,
) -> tuple[bool, str | None]:
    """Verify release review exists, passed, and matches final + source hashes."""
    if not final_video.is_file():
        return False, f"最终视频不存在: {final_video}"

    review = load_video_release_review(ep_dir)
    if review is None:
        return False, "缺少或损坏 work/qa/video-release-review.json"
    if review.get("final_status") != "READY_TO_PUBLISH":
        return False, f"视频发布验收状态不是 READY_TO_PUBLISH: {review.get('final_status')}"

    try:
        reviewed_path = _resolve_inside_episode(ep_dir.resolve(), str(review.get("reviewed_video") or ""))
    except VideoReleaseReviewError as exc:
        return False, str(exc)
    if reviewed_path != final_video.resolve():
        return False, "发布验收绑定的不是当前最终视频"

    current_hash = sha256_file(final_video)
    if review.get("video_sha256") != current_hash:
        return False, "最终视频已重新渲染/修改，旧发布验收 SHA256 已失效"

    source_review = review.get("source_fidelity_review")
    if not isinstance(source_review, dict):
        return False, "发布验收缺少 source_fidelity_review"
    try:
        _validate_source_artifacts(ep_dir.resolve(), source_review)
        _validate_source_ready(source_review)
    except VideoReleaseReviewError as exc:
        return False, str(exc)

    continuous = review.get("continuous_playback_review")
    if not isinstance(continuous, dict):
        return False, "发布验收缺少 continuous_playback_review"
    try:
        _validate_ready_to_publish(continuous)
    except VideoReleaseReviewError as exc:
        return False, str(exc)

    return True, None
