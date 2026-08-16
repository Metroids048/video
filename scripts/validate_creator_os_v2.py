from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_CONFIG = [
    "project.yaml", "workflow.yaml", "platforms.yaml", "visual.yaml",
    "audio.yaml", "quality.yaml", "providers.yaml", "content-pillars.yaml",
    "creator-workflow.yaml", "production-types.yaml", "content-formats.yaml",
    "reference-acquisition.yaml", "voice.yaml",
]

REQUIRED_SCHEMAS = [
    "creative-contract.schema.json", "format-decision.schema.json",
    "voice-profile.schema.json", "creator-review.schema.json",
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
    if project.get("name") != "Creator OS" or str(project.get("version")) != "2.0":
        errors.append("project.yaml is not Creator OS 2.0")
    if project.get("publish_success_state") != "READY_TO_PUBLISH":
        errors.append("publish success state is not READY_TO_PUBLISH")

    workflow = loaded.get("workflow.yaml", {}).get("workflow", {})
    lifecycle = workflow.get("public_lifecycle", [])
    if not lifecycle or lifecycle[-1] != "READY_TO_PUBLISH":
        errors.append("public lifecycle does not end in READY_TO_PUBLISH")
    if workflow.get("repair", {}).get("max_rounds") != 3:
        errors.append("repair max_rounds must be 3")

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
    print("protected capability resources: present")
    print("legacy quant/EP01 residue checks: clear")
    return 0


if __name__ == "__main__":
    sys.exit(main())
