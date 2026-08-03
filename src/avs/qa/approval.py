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

    Args:
        ep_dir: Episode directory
        episode_id: Episode ID
        reviewer: Name of the human reviewer
        video_path: Absolute path to the video being approved
        checklist: Dict with required keys or None to use all True
        notes: Optional review notes

    Returns:
        The approval record dict

    Raises:
        FileNotFoundError: If video does not exist
        ValueError: If checklist is invalid or any item is False when approved=True
    """
    if not video_path.is_file():
        raise FileNotFoundError(f"视频不存在: {video_path}")

    video_sha256 = sha256_file(video_path)
    relative_path = video_path.relative_to(ep_dir).as_posix()

    # Default checklist: all True
    if checklist is None:
        checklist = {
            "hook_clear_within_3s": True,
            "captions_readable": True,
            "composition_acceptable": True,
            "audio_acceptable": True,
            "no_placeholders": True,
            "facts_and_rights_checked": True,
        }

    # Validate checklist has all required keys
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

    # If any checklist item is False, cannot approve
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
    """Load visual approval if it exists and is valid.

    Returns:
        Approval dict if exists and valid, None otherwise
    """
    approval_path = ep_dir / "delivery" / "visual-approval.json"
    if not approval_path.is_file():
        return None

    try:
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        _validate_approval(ep_dir, approval)
        return approval
    except Exception:
        # Invalid approval is treated as missing
        return None


def verify_approval_current(ep_dir: Path, final_video: Path) -> tuple[bool, str | None]:
    """Verify that approval matches the current final video hash.

    Returns:
        (is_valid, error_message)
        - (True, None) if approval exists and hash matches
        - (False, reason) otherwise
    """
    approval = load_approval(ep_dir)
    if approval is None:
        return False, "缺少人工视觉批准文件"

    if not approval.get("approved"):
        return False, "批准文件中 approved=false"

    if not final_video.is_file():
        return False, f"最终视频不存在: {final_video}"

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
        return False, "输入、Script、Shot Plan、Timeline 或视频已变更，批准指纹失效"

    return True, None


def save_approval(ep_dir: Path, approval: dict[str, Any]) -> Path:
    """Save approval to delivery/visual-approval.json.

    Args:
        ep_dir: Episode directory
        approval: Validated approval dict

    Returns:
        Path to saved approval file
    """
    _validate_approval(ep_dir, approval)

    delivery_dir = ep_dir / "delivery"
    delivery_dir.mkdir(parents=True, exist_ok=True)

    approval_path = delivery_dir / "visual-approval.json"
    approval_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8")

    return approval_path
