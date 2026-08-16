from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_CONFIG = [
    "project.yaml", "workflow.yaml", "platforms.yaml", "visual.yaml",
    "audio.yaml", "quality.yaml", "video-review.yaml", "providers.yaml",
    "content-pillars.yaml", "creator-workflow.yaml", "production-types.yaml",
    "content-formats.yaml", "reference-acquisition.yaml", "voice.yaml",
]

REQUIRED_SCHEMAS = [
    "creative-contract.schema.json", "format-decision.schema.json",
    "voice-profile.schema.json", "creator-review.schema.json",
    "video-release-review.schema.json",
]

PROTECTED = [
    "skills-src", "third_party_skills", "vendor", ".agents/skills", ".claude/skills",
    "skills.lock.json", "tools-manifest.yaml",
]

FORBIDDEN = [
    "fixtures/golden-ai-quant",
    "docs/ai-pm-media-business-plan.md",
    "AI量化交易视频项目完成报告.md",
    "AI量化交易账号完整方案.md",
    "FINAL_COMPLETION_REPORT.md",
    "FINAL_EXECUTION_REPORT.md",
    "FINAL_VIDEO_QUALITY_CLOSURE.md",
    "scripts/build_ep01_v4.py", "scripts/build_ep01_v5.py", "scripts/build_ep01_v6.py",
    "scripts/build_ep01_v7.py", "scripts/build_ep01_v8.py", "scripts/build_ep01_final.py",
    "scripts/build_ep01_final_final_lock.py",
]


def main() -> int:
    errors: list[str] = []
    loaded: dict[str, dict] = {}

    for name in REQUIRED_CONFIG:
        path = ROOT / "config" / name
        if not path.exists():
            errors.append(f"missing config: {path.relative_to(ROOT)}")
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"invalid yaml {name}: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"config root is not mapping: {name}")
            continue
        loaded[name] = data

    for name in REQUIRED_SCHEMAS:
        path = ROOT / "schemas" / name
        if not path.exists():
            errors.append(f"missing schema: {path.relative_to(ROOT)}")
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"invalid json {name}: {exc}")

    for rel in PROTECTED:
        if not (ROOT / rel).exists():
            errors.append(f"protected resource missing: {rel}")

    for rel in FORBIDDEN:
        if (ROOT / rel).exists():
            errors.append(f"legacy residue still present: {rel}")

    project = loaded.get("project.yaml", {}).get("project", {})
    if project.get("name") != "Creator OS" or str(project.get("version")) != "2.3":
        errors.append("project.yaml is not Creator OS 2.3")
    if project.get("publish_success_state") != "READY_TO_PUBLISH":
        errors.append("publish success state is not READY_TO_PUBLISH")
    for key in (
        "release_gate_fail_closed",
        "delivery_requires_current_video_release_review",
        "release_review_must_match_current_sha256",
        "release_review_must_match_current_source_sha256s",
        "release_review_requires_source_to_final_fidelity",
    ):
        if project.get(key) is not True:
            errors.append(f"project contract missing: {key}")

    principles = loaded.get("project.yaml", {}).get("principles", {})
    for key in (
        "source_fidelity_before_canvas_fill",
        "full_frame_context_before_roi",
        "preserve_spatial_continuity",
        "preserve_temporal_continuity",
        "destructive_crop_requires_explicit_authorization",
        "mobile_preview_is_qa_only",
        "formal_video_delivery_is_single_1080x1920_master",
    ):
        if principles.get(key) is not True:
            errors.append(f"project principle missing: {key}")
    if principles.get("landscape_screen_recording_default") != "fit_full_frame":
        errors.append("landscape screen recording default must be fit_full_frame")

    workflow = loaded.get("workflow.yaml", {}).get("workflow", {})
    lifecycle = workflow.get("public_lifecycle", [])
    if not lifecycle or lifecycle[-1] != "READY_TO_PUBLISH":
        errors.append("public lifecycle does not end in READY_TO_PUBLISH")
    if workflow.get("repair", {}).get("max_rounds") != 3:
        errors.append("repair max_rounds must be 3")
    release_gate = workflow.get("video_release_gate", {})
    for key in (
        "fail_closed",
        "delivery_must_reverify_gate",
        "requires_source_inventory",
        "requires_source_to_final_fidelity_review",
        "requires_current_source_sha256s",
        "requires_current_final_sha256",
    ):
        if release_gate.get(key) is not True:
            errors.append(f"workflow video_release_gate missing: {key}")

    visual = loaded.get("visual.yaml", {}).get("visual", {})
    screen = visual.get("screen_recording", {})
    if screen.get("landscape_strategy") != "fit_full_frame":
        errors.append("visual landscape strategy must be fit_full_frame")
    if screen.get("preserve_full_source_frame_by_default") is not True:
        errors.append("visual must preserve full source frame by default")
    if screen.get("destructive_crop_requires_explicit_authorization") is not True:
        errors.append("visual destructive crop must require explicit authorization")
    if screen.get("unauthorized_destructive_crop_falls_back_to") != "fit_full_frame":
        errors.append("unauthorized destructive crop must fall back to fit_full_frame")
    mobile = visual.get("mobile_preview", {})
    if mobile.get("qa_only") is not True or mobile.get("include_in_delivery") is not False:
        errors.append("360x640 mobile preview must be QA-only and excluded from delivery")

    review = loaded.get("video-review.yaml", {}).get("video_review", {})
    source_truth = review.get("source_of_truth")
    if not isinstance(source_truth, list) or "original source artifacts actually used" not in source_truth:
        errors.append("video-review source_of_truth must include actual source artifacts")
    hard_fails = review.get("hard_fail_conditions", {})
    for key in (
        "source_to_final_fidelity_not_verified",
        "source_artifact_hash_missing_or_stale",
        "unauthorized_destructive_crop",
        "source_frame_context_lost",
        "spatial_continuity_broken",
        "temporal_continuity_broken",
        "first_frame_partial_or_mid_action",
        "abrupt_or_discontinuous_opening",
        "slideshow_feel",
        "static_screenshot_pan_zoom_dominant",
        "key_evidence_requires_pause",
        "unreadable_evidence_due_to_short_dwell",
        "rapid_dark_light_switching",
    ):
        if hard_fails.get(key, {}).get("fail") is not True:
            errors.append(f"video-review hard fail missing: {key}")
    delivery_gate = review.get("delivery_gate", {})
    for key in (
        "current_sha256_match_required",
        "current_source_sha256s_match_required",
        "source_fidelity_pass_required",
        "delivery_requires_zero_known_critical_findings",
        "mobile_preview_is_qa_only",
    ):
        if delivery_gate.get(key) is not True:
            errors.append(f"video-review delivery gate missing: {key}")

    quality = loaded.get("quality.yaml", {}).get("quality", {})
    if quality.get("release_gate", {}).get("fail_closed") is not True:
        errors.append("quality release gate must fail closed")
    publishable = quality.get("publishable", {})
    for key in (
        "require_video_release_review_record",
        "require_source_to_final_fidelity_review",
        "require_source_artifact_hashes",
        "require_spatial_continuity_review",
        "require_temporal_continuity_review",
        "require_no_unauthorized_destructive_crop",
    ):
        if publishable.get(key) is not True:
            errors.append(f"publishable video contract missing: {key}")
    composition = quality.get("composition", {})
    if composition.get("landscape_default_layout") != "fit_full_frame":
        errors.append("quality landscape_default_layout must be fit_full_frame")
    if composition.get("destructive_crop_requires_explicit_authorization") is not True:
        errors.append("quality destructive crop authorization gate missing")

    formats = set(loaded.get("content-formats.yaml", {}).get("format_router", {}).get("allowed", []))
    if formats != {"VIDEO", "CAROUSEL", "TEXT"}:
        errors.append(f"unexpected format set: {sorted(formats)}")

    pillars = loaded.get("content-pillars.yaml", {}).get("content_pillars", {})
    if pillars.get("default_mode") != "ORIGINAL":
        errors.append("content default_mode must be ORIGINAL")

    douyin = loaded.get("reference-acquisition.yaml", {}).get("reference_acquisition", {}).get("sources", {}).get("douyin_url", {})
    if douyin.get("failure_behavior") != "degrade_honestly":
        errors.append("Douyin acquisition must degrade_honestly")

    timing = loaded.get("voice.yaml", {}).get("voice", {}).get("video_timing", {})
    if not timing.get("narration_master_is_clock") or not timing.get("forbid_character_count_timing"):
        errors.append("video timing contract is not narration-master/word-timestamp based")

    if errors:
        print("CREATOR OS V2 VALIDATION: FAIL")
        for item in errors:
            print(f"- {item}")
        return 1

    print("CREATOR OS V2 VALIDATION: PASS")
    print(f"configs: {len(REQUIRED_CONFIG)}")
    print(f"schemas: {len(REQUIRED_SCHEMAS)}")
    print("video release gate: fail-closed + final/source SHA256 bound + source fidelity required")
    print("landscape screen recording: fit_full_frame default; destructive crop explicit-only")
    print("mobile 360x640: QA-only; formal delivery is one 1080x1920 master")
    print("protected capability resources: present")
    print("legacy quant/EP01 residue checks: clear")
    return 0


if __name__ == "__main__":
    sys.exit(main())
