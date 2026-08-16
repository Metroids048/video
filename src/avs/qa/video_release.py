"""Fail-closed pre-delivery review for the exact rendered video artifact.

This gate intentionally does not try to infer publish quality from metadata.
It validates a reviewer-produced record that confirms a real 1x start-to-end
watch, dense first-10-second inspection, transition scan, mobile preview and
actual audio listening.  The record is content-addressed to the reviewed MP4 so
any rerender invalidates the previous approval.
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
        raise VideoReleaseReviewError(f"reviewed_video 路径逃逸 Episode: {raw}") from exc
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
    """Validate reviewer input and bind it to the exact current MP4.

    A REPAIRING/BLOCKED record may be saved to preserve findings.  A
    READY_TO_PUBLISH record is accepted only when every continuous-review hard
    gate passes.
    """
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
    """Verify release review exists, passed, and matches the exact final MP4."""
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

    continuous = review.get("continuous_playback_review")
    if not isinstance(continuous, dict):
        return False, "发布验收缺少 continuous_playback_review"
    try:
        _validate_ready_to_publish(continuous)
    except VideoReleaseReviewError as exc:
        return False, str(exc)

    return True, None
