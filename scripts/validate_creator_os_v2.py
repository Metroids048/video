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
    if project.get("name") != "Creator OS" or str(project.get("version")) != "2.2":
        errors.append("project.yaml is not Creator OS 2.2")
    if project.get("publish_success_state") != "READY_TO_PUBLISH":
        errors.append("publish success state is not READY_TO_PUBLISH")
    if project.get("release_gate_fail_closed") is not True:
        errors.append("video release gate must fail closed")
    if project.get("delivery_requires_current_video_release_review") is not True:
        errors.append("delivery must require current video release review")
    if project.get("release_review_must_match_current_sha256") is not True:
        errors.append("release review must match current SHA256")

    workflow = loaded.get("workflow.yaml", {}).get("workflow", {})
    lifecycle = workflow.get("public_lifecycle", [])
    if not lifecycle or lifecycle[-1] != "READY_TO_PUBLISH":
        errors.append("public lifecycle does not end in READY_TO_PUBLISH")
    if workflow.get("repair", {}).get("max_rounds") != 3:
        errors.append("repair max_rounds must be 3")
    release_gate = workflow.get("video_release_gate", {})
    if release_gate.get("fail_closed") is not True:
        errors.append("workflow video_release_gate must fail closed")
    if release_gate.get("delivery_must_reverify_gate") is not True:
        errors.append("delivery must reverify release gate")

    review = loaded.get("video-review.yaml", {}).get("video_review", {})
    if review.get("source_of_truth") != "actual rendered video pixels and audible audio":
        errors.append("video-review source_of_truth must be actual rendered media")
    hard_fails = review.get("hard_fail_conditions", {})
    for key in (
        "abrupt_or_discontinuous_opening",
        "slideshow_feel",
        "static_screenshot_pan_zoom_dominant",
        "key_evidence_requires_pause",
        "unreadable_evidence_due_to_short_dwell",
        "rapid_dark_light_switching",
    ):
        if hard_fails.get(key, {}).get("fail") is not True:
            errors.append(f"video-review hard fail missing: {key}")
    if review.get("delivery_gate", {}).get("current_sha256_match_required") is not True:
        errors.append("video release delivery gate must require current SHA256")

    quality = loaded.get("quality.yaml", {}).get("quality", {})
    if quality.get("release_gate", {}).get("fail_closed") is not True:
        errors.append("quality release gate must fail closed")
    if quality.get("publishable", {}).get("require_video_release_review_record") is not True:
        errors.append("publishable video must require release-review record")

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
    print("video release gate: fail-closed + current SHA256 bound")
    print("protected capability resources: present")
    print("legacy quant/EP01 residue checks: clear")
    return 0


if __name__ == "__main__":
    sys.exit(main())
