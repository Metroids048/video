"""Validation for Agent-authored publishable scripts.

Schema validation only proves a script is well-formed.  These checks prove it is
*trustworthy*: that its evidence claims point at assets that actually exist, that
it has not smuggled in placeholder text, and that it is not just the
deterministic fact-join wearing an ``authored_by: agent`` label.

Without this layer, letting an Agent write the publishable script would trade a
predictably bad script for an unpredictably wrong one.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import jsonschema

_SCHEMA = Path(__file__).resolve().parents[3] / "schemas" / "active-script.schema.json"

SCRIPT_RELATIVE = "work/content/script.json"

# Text that means the Agent left the job unfinished.
_PLACEHOLDER_PATTERNS = (
    r"\bTODO\b", r"\bFIXME\b", r"\bTBD\b", r"待补充", r"占位", r"placeholder",
    r"lorem ipsum", r"xxx+", r"\bN/?A\b",
)
# The deterministic planner's signature: facts glued with full-width semicolons.
_FACT_JOIN_MIN_SEGMENTS = 2
_FACT_JOIN_RATIO = 0.6

MIN_SEGMENT_DURATION = 0.8
MAX_SEGMENT_DURATION = 12.0
MAX_SPOKEN_CHARS_PER_SECOND = 9.0
MIN_SPOKEN_CHARS_PER_SECOND = 1.5
VISUAL_SOURCE_TYPES = frozenset({"screenshot", "recording", "video"})


class AgentScriptError(ValueError):
    """An Agent-authored script cannot be trusted for the publishable path."""


def _schema() -> dict[str, Any]:
    return json.loads(_SCHEMA.read_text(encoding="utf-8"))


def script_path(episode_dir: Path) -> Path:
    return episode_dir / "work" / "content" / "script.json"


def is_agent_authored(script: dict[str, Any]) -> bool:
    return str(script.get("authored_by") or "deterministic") == "agent"


def load_agent_script(episode_dir: Path) -> dict[str, Any] | None:
    """Return the script only when it exists and claims Agent authorship."""
    path = script_path(episode_dir)
    if not path.is_file():
        return None
    try:
        script = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(script, dict) or not is_agent_authored(script):
        return None
    return script


def _visual_asset_ids(manifest: dict[str, Any]) -> set[str]:
    return {
        str(asset.get("asset_id"))
        for asset in manifest.get("assets", [])
        if asset.get("source_type") in VISUAL_SOURCE_TYPES
    }


def _known_regions(intelligence: dict[str, Any]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for asset in intelligence.get("assets", []):
        asset_id = str(asset.get("asset_id"))
        pairs.add((asset_id, "full-frame"))
        for region in asset.get("regions", []):
            pairs.add((asset_id, str(region.get("region_id"))))
    return pairs


def _looks_like_fact_join(segments: list[dict[str, Any]]) -> bool:
    """Detect the deterministic planner's output relabelled as Agent work."""
    body = [item for item in segments if item.get("evidence_required")]
    if len(body) < _FACT_JOIN_MIN_SEGMENTS:
        return False
    joined = sum(1 for item in body if str(item.get("spoken_text", "")).count("；") >= 1)
    return joined / len(body) >= _FACT_JOIN_RATIO


def validate_agent_script(
    script: dict[str, Any],
    *,
    manifest: dict[str, Any],
    intelligence: dict[str, Any],
    episode_id: str | None = None,
) -> list[str]:
    """Return every reason the script must not be trusted. Empty list = usable."""
    errors: list[str] = []
    try:
        jsonschema.Draft7Validator(_schema()).validate(script)
    except jsonschema.ValidationError as exc:
        return [f"Schema 校验失败: {exc.message}"]

    if episode_id is not None and script.get("episode_id") != episode_id:
        errors.append(
            f"episode_id 不匹配: 脚本为 {script.get('episode_id')!r}，Episode 为 {episode_id!r}"
        )

    segments = list(script.get("segments", []))
    if not segments:
        return errors + ["脚本没有任何 segment"]

    seen_ids: set[str] = set()
    visual_assets = _visual_asset_ids(manifest)
    known_regions = _known_regions(intelligence)

    for index, segment in enumerate(segments):
        label = str(segment.get("segment_id") or f"#{index + 1}")
        if label in seen_ids:
            errors.append(f"{label}: segment_id 重复")
        seen_ids.add(label)

        spoken = str(segment.get("spoken_text", "")).strip()
        if not spoken:
            errors.append(f"{label}: spoken_text 为空")
            continue
        for pattern in _PLACEHOLDER_PATTERNS:
            if re.search(pattern, spoken, re.IGNORECASE):
                errors.append(f"{label}: spoken_text 含占位符文本 ({pattern})")
                break

        duration = float(segment.get("duration_seconds", 0.0))
        if not MIN_SEGMENT_DURATION <= duration <= MAX_SEGMENT_DURATION:
            errors.append(
                f"{label}: duration_seconds={duration} 超出 "
                f"[{MIN_SEGMENT_DURATION}, {MAX_SEGMENT_DURATION}]"
            )
        else:
            # Narration that cannot physically be read in the allotted time will
            # either be cut off or force the TTS into an unnatural rate.
            density = len(spoken.replace(" ", "")) / duration
            if density > MAX_SPOKEN_CHARS_PER_SECOND:
                errors.append(
                    f"{label}: {density:.1f} 字/秒 超过 {MAX_SPOKEN_CHARS_PER_SECOND}，"
                    "配音会被截断或语速失真"
                )
            elif density < MIN_SPOKEN_CHARS_PER_SECOND:
                errors.append(
                    f"{label}: {density:.1f} 字/秒 低于 {MIN_SPOKEN_CHARS_PER_SECOND}，"
                    "画面会长时间停滞"
                )

        refs = list(segment.get("asset_refs", []))
        if segment.get("evidence_required"):
            if not refs:
                errors.append(f"{label}: evidence_required 为 true 但没有 asset_refs")
            for ref in refs:
                asset_id = str(ref.get("asset_id") or "")
                if asset_id not in visual_assets:
                    errors.append(
                        f"{label}: asset_ref {asset_id!r} 不是清单中的视觉素材，"
                        "不能作为画面证据"
                    )
                    continue
                region_id = str(ref.get("region_id") or "full-frame")
                if (asset_id, region_id) not in known_regions:
                    errors.append(
                        f"{label}: {asset_id} 不存在区域 {region_id!r}，"
                        "证据区域必须来自真实分析结果"
                    )
        elif refs:
            errors.append(
                f"{label}: evidence_required 为 false 却绑定了 asset_refs，"
                "证据边界必须明确"
            )

    hook = segments[0]
    if hook.get("evidence_required"):
        errors.append("首段必须是 Hook 且 evidence_required 为 false")
    if not str(hook.get("spoken_text", "")).strip():
        errors.append("首段 Hook 的 spoken_text 为空")

    if _looks_like_fact_join(segments):
        errors.append(
            "多数证据段落是分号拼接的事实列表，与确定性规划器输出无区别；"
            "标记为 agent 撰写但没有真正创作"
        )

    total = sum(float(item.get("duration_seconds", 0.0)) for item in segments)
    if total <= 0:
        errors.append("脚本总时长为 0")

    return errors


def assert_agent_script(
    script: dict[str, Any],
    *,
    manifest: dict[str, Any],
    intelligence: dict[str, Any],
    episode_id: str | None = None,
) -> dict[str, Any]:
    """Validate and return the script, raising ``AgentScriptError`` on any issue."""
    errors = validate_agent_script(
        script, manifest=manifest, intelligence=intelligence, episode_id=episode_id,
    )
    if errors:
        raise AgentScriptError("; ".join(errors))
    return script


def script_summary(script: dict[str, Any]) -> dict[str, Any]:
    segments = list(script.get("segments", []))
    return {
        "authored_by": script.get("authored_by", "deterministic"),
        "author_id": script.get("author_id"),
        "hook_variant": script.get("hook_variant"),
        "segment_count": len(segments),
        "total_duration": round(
            sum(float(item.get("duration_seconds", 0.0)) for item in segments), 2
        ),
        "evidence_segments": sum(1 for item in segments if item.get("evidence_required")),
        "has_narrative_beats": any(item.get("narrative_beat") for item in segments),
        "has_visual_goals": any(item.get("visual_goal") for item in segments),
    }
