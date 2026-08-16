"""Human visual approval with content-addressed binding."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def artifact_fingerprint(ep_dir: Path, video_path: Path) -> str:
    """Hash every artifact whose change invalidates visual approval."""
    paths = (
        ep_dir / "work" / "input-manifest.json",
        ep_dir / "work" / "content" / "script.json",
        ep_dir / "work" / "content" / "evidence-map.json",
        ep_dir / "work" / "content" / "shot-plan.json",
        ep_dir / "work" / "timeline.json",
        ep_dir / "work" / "qa" / "video-release-review.json",
        video_path,
    )
    hasher = hashlib.sha256()
    for path in paths:
        hasher.update(path.relative_to(ep_dir).as_posix().encode("utf-8"))
        hasher.update(sha256_file(path).encode("ascii") if path.is_file() else b"MISSING")
    return hasher.hexdigest()


def _project_root(ep_dir: Path) -> Path:
    """Locate project root by finding schemas directory."""
    for candidate in (ep_dir, *ep_dir.parents):
        if (candidate / "schemas" / "visual-approval.schema.json").is_file():
            return candidate
    raise FileNotFoundError("无法定位 schemas/visual-approval.schema.json")


def _validate_approval(ep_dir: Path, approval: dict[str, Any]) -> None:
    """Validate approval against schema."""
    schema_path = _project_root(ep_dir) / "schemas" / "visual-approval.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(approval)


def _require_current_release_review(ep_dir: Path, video_path: Path) -> None:
    """Fail closed unless the exact MP4 passed continuous pre-delivery review."""
    from avs.qa.video_release import verify_video_release_review_current

    valid, reason = verify_video_release_review_current(ep_dir, video_path)
    if not valid:
        raise ValueError(
            "视频发布验收未通过，不能批准/交付。"
            + (reason or "请执行完整 1x 连续观看并生成当前 SHA256 的 release review")
        )


def create_approval(
    ep_dir: Path,
    episode_id: str,
    reviewer: str,
    video_path: Path,
    *,
    checklist: dict[str, bool] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Create a visual approval record bound to the current video hash.

    Human approval is downstream of the independent video-release gate.  The
    exact MP4 must already have passed a full 1x start-to-end review; otherwise
    approval is refused.
    """
    if not video_path.is_file():
        raise FileNotFoundError(f"视频不存在: {video_path}")

    _require_current_release_review(ep_dir, video_path)

    video_sha256 = sha256_file(video_path)
    relative_path = video_path.relative_to(ep_dir).as_posix()

    if checklist is None:
        checklist = {
            "hook_clear_within_3s": True,
            "captions_readable": True,
            "composition_acceptable": True,
            "audio_acceptable": True,
            "no_placeholders": True,
            "facts_and_rights_checked": True,
        }

    required_keys = {
        "hook_clear_within_3s",
        "captions_readable",
        "composition_acceptable",
        "audio_acceptable",
        "no_placeholders",
        "facts_and_rights_checked",
    }
    if set(checklist.keys()) != required_keys:
        raise ValueError(f"checklist 必须包含且仅包含以下键: {required_keys}")

    if not all(checklist.values()):
        raise ValueError("任一 checklist 项为 false 时不得 approved=True")

    approval: dict[str, Any] = {
        "episode_id": episode_id,
        "approved": True,
        "reviewer": reviewer,
        "video_path": relative_path,
        "video_sha256": video_sha256,
        "artifact_fingerprint": artifact_fingerprint(ep_dir, video_path),
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "checklist": checklist,
        "notes": notes,
    }

    _validate_approval(ep_dir, approval)
    return approval


def load_approval(ep_dir: Path) -> dict[str, Any] | None:
    """Load visual approval if it exists and is valid."""
    approval_path = ep_dir / "delivery" / "visual-approval.json"
    if not approval_path.is_file():
        return None

    try:
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        _validate_approval(ep_dir, approval)
        return approval
    except Exception:
        return None


def verify_approval_current(ep_dir: Path, final_video: Path) -> tuple[bool, str | None]:
    """Verify human approval AND machine release review match the current MP4."""
    approval = load_approval(ep_dir)
    if approval is None:
        return False, "缺少人工视觉批准文件"

    if not approval.get("approved"):
        return False, "批准文件中 approved=false"

    if not final_video.is_file():
        return False, f"最终视频不存在: {final_video}"

    try:
        _require_current_release_review(ep_dir, final_video)
    except ValueError as exc:
        return False, str(exc)

    current_hash = sha256_file(final_video)
    approval_hash = approval.get("video_sha256", "")

    if current_hash != approval_hash:
        return False, (
            f"视频已变更：批准哈希 {approval_hash[:16]}...，"
            f"当前哈希 {current_hash[:16]}..."
        )

    approved_fingerprint = approval.get("artifact_fingerprint")
    if (ep_dir / "work" / "content" / "shot-plan.json").is_file() and not approved_fingerprint:
        return False, "Active Episode 的人工批准缺少完整 Artifact Fingerprint"
    if approved_fingerprint and approved_fingerprint != artifact_fingerprint(ep_dir, final_video):
        return False, "输入、Script、Shot Plan、Timeline、Release Review 或视频已变更，批准指纹失效"

    return True, None


def save_approval(ep_dir: Path, approval: dict[str, Any]) -> Path:
    """Save approval to delivery/visual-approval.json."""
    _validate_approval(ep_dir, approval)

    delivery_dir = ep_dir / "delivery"
    delivery_dir.mkdir(parents=True, exist_ok=True)

    approval_path = delivery_dir / "visual-approval.json"
    approval_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8")

    return approval_path
