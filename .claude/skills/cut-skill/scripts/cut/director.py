"""cut.director — turn a one-line brief into an executable edit plan."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SHORT_FORM_HINTS = ("短视频", "抖音", "douyin", "tiktok", "reels", "shorts", "快手", "小红书", "vlog")
LONG_FORM_HINTS = ("长视频", "影视", "解说", "纪录片", "访谈", "课程", "30分钟", "半小时", "长片")
FAST_HINTS = ("节奏轻快", "快节奏", "卡点", "燃", "高能", "带感", "vlog")
STEADY_HINTS = ("沉稳", "电影感", "叙事", "纪录", "解说", "长视频")


def _prompt(prompt: str) -> str:
    return (prompt or "").strip().lower()


def _duration_from_prompt(prompt: str, default_us: int) -> int:
    raw = prompt or ""
    minute = re.search(r"(\d+(?:\.\d+)?)\s*(分钟|min|minute)", raw, re.I)
    if minute:
        return int(float(minute.group(1)) * 60_000_000)
    second = re.search(r"(\d+(?:\.\d+)?)\s*(秒|s|sec|second)", raw, re.I)
    if second:
        return int(float(second.group(1)) * 1_000_000)
    return default_us


def _target_platform(prompt: str) -> str:
    p = _prompt(prompt)
    if "抖音" in p or "douyin" in p:
        return "douyin"
    if "tiktok" in p:
        return "tiktok"
    if "小红书" in p:
        return "xiaohongshu"
    if "快手" in p:
        return "kuaishou"
    if "youtube" in p:
        return "youtube"
    if "b站" in p or "bilibili" in p:
        return "bilibili"
    return "generic"


def _format(prompt: str) -> str:
    p = _prompt(prompt)
    if any(h in p for h in LONG_FORM_HINTS):
        return "long_form"
    if any(h in p for h in SHORT_FORM_HINTS):
        return "short_form"
    return "short_form"


def _style(prompt: str, fmt: str) -> Dict[str, Any]:
    p = _prompt(prompt)
    if any(h in p for h in STEADY_HINTS) or fmt == "long_form":
        pace = "steady"
        transition_policy = "motivated_cuts"
        color = "cinematic"
    elif any(h in p for h in FAST_HINTS):
        pace = "fast"
        transition_policy = "beat_matched"
        color = "warm"
    else:
        pace = "medium"
        transition_policy = "clean_cuts"
        color = "natural"
    return {
        "pace": pace,
        "transition_policy": transition_policy,
        "color": color,
        "subtitle_style": "burned_in_readable",
        "audio_policy": "duck_voice_under_bgm",
    }


def _normalize_assets(assets: Optional[Iterable[Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in assets or []:
        if isinstance(item, dict):
            data = dict(item)
        else:
            data = {"path": str(item)}
        path = data.get("path", "")
        suffix = Path(path).suffix.lower()
        if "type" not in data:
            if suffix in (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"):
                data["type"] = "audio"
            elif suffix in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
                data["type"] = "image"
            else:
                data["type"] = "video"
        data.setdefault("role", "bgm" if data["type"] == "audio" else "source")
        out.append(data)
    return out


def create_edit_plan(
    brief: str,
    assets: Optional[Iterable[Any]] = None,
    backend: str = "jianying",
    project: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a deterministic professional edit plan from a short user brief."""
    normalized_assets = _normalize_assets(assets)
    fmt = _format(brief)
    default_duration = 60_000_000 if fmt == "short_form" else 1_800_000_000
    duration_us = _duration_from_prompt(brief, default_duration)
    style = _style(brief, fmt)

    steps = [
        {"action": "detect", "reason": "confirm available editing backends"},
        {"action": "get_state", "backend": backend, "project": project, "required": True},
        {
            "action": "ingest_assets",
            "assets_count": len(normalized_assets),
            "selection_policy": "prefer sharp, stable, high-energy shots" if fmt == "short_form" else "preserve narrative continuity",
        },
        {
            "action": "assemble_rough_cut",
            "target_duration_us": duration_us,
            "pacing": style["pace"],
        },
        {
            "action": "add_subtitles",
            "mode": "asr_if_voice_detected",
            "style": style["subtitle_style"],
        },
        {
            "action": "sound_mix",
            "policy": style["audio_policy"],
            "ducking": {"level": 0.28 if fmt == "short_form" else 0.4, "fade_us": 180_000},
        },
        {
            "action": "color_grade",
            "look": style["color"],
        },
        {
            "action": "export",
            "preset": "h264_1080p" if fmt == "short_form" else "h264_match_source",
        },
        {"action": "quality_check", "required": True},
    ]

    if style["transition_policy"] == "beat_matched":
        steps.insert(4, {"action": "add_transitions", "policy": "beat_matched", "max_duration_us": 350_000})

    return {
        "brief": brief,
        "backend": backend,
        "project": project,
        "format": fmt,
        "target_platform": _target_platform(brief),
        "target_duration_us": duration_us,
        "style": style,
        "story_structure": ["hook", "setup", "development", "turning_point", "payoff"],
        "assets": normalized_assets,
        "steps": steps,
        "qa_required": True,
    }


def plan_to_cli_preview(plan: Dict[str, Any]) -> List[str]:
    """Return safe, human-readable CLI commands for the non-destructive plan steps."""
    backend = plan.get("backend", "jianying")
    project = plan.get("project")
    project_part = f" --project {project}" if project else ""
    return [
        "python -m cut.cli detect",
        f"python -m cut.cli get-state --backend {backend}{project_part}",
        "# Execute the edit decision list with cut.director or individual cut.cli commands.",
        "# Run export, then python -m cut.cli qa --output <file> --expected-duration <time>.",
    ]


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Create a professional edit plan from a one-line brief.")
    parser.add_argument("brief")
    parser.add_argument("--backend", default="jianying", choices=["jianying", "capcut", "premiere"])
    parser.add_argument("--project")
    parser.add_argument("--asset", action="append", default=[])
    args = parser.parse_args(argv)

    plan = create_edit_plan(args.brief, args.asset, backend=args.backend, project=args.project)
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
