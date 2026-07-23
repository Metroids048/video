"""src/avs/reference/recipe.py — 生成 reference-recipe.json。"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from avs.reference.shots import Shot

log = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "reference-recipe.schema.json"


def _load_schema() -> dict:
    with _SCHEMA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def recipe_path(episode_dir: Path) -> Path:
    return episode_dir / "work" / "reference" / "reference-recipe.json"


def build_recipe(
    episode_id: str,
    source_asset_id: str,
    probe: dict[str, Any],
    shots: list[Shot],
    keyframe_paths: dict[str, Path],
    episode_dir: Path,
    transcript_text: str | None = None,
) -> dict[str, Any]:
    """构建 reference-recipe.json 数据字典（不写磁盘）。"""
    ep_dir = episode_dir.resolve()

    shots_list: list[dict] = []
    for shot in shots:
        kf = keyframe_paths.get(shot.shot_id)
        kf_rel = kf.relative_to(ep_dir).as_posix() if kf and kf.exists() else None

        # 从 transcript 分配文本片段（粗略按时间比例）
        shot_text: str | None = None
        if transcript_text and probe.get("duration"):
            dur = probe["duration"]
            ratio_start = shot.start / dur
            ratio_end = shot.end / dur
            tokens = transcript_text.split()
            n = len(tokens)
            si = int(n * ratio_start)
            ei = int(n * ratio_end)
            chunk = " ".join(tokens[si:ei]).strip()
            shot_text = chunk if chunk else None

        shots_list.append({
            "shot_id": shot.shot_id,
            "start": round(shot.start, 3),
            "end": round(shot.end, 3),
            "keyframe_path": kf_rel,
            "transcript": shot_text,
            "shot_type": shot.shot_type,
            "confidence": round(shot.confidence, 3),
        })

    # 可迁移规则（确定性分析，不虚构）
    transferable: list[str] = []
    dur = probe.get("duration") or 0
    n_shots = len(shots)
    if dur > 0:
        pace = n_shots / dur
        if pace > 1.0:
            transferable.append(f"快速切镜节奏（约 {pace:.1f} 镜/秒）")
        elif pace < 0.3:
            transferable.append(f"缓慢稳定节奏（约 {pace:.1f} 镜/秒）")
    if probe.get("has_audio") is False:
        transferable.append("无音轨（纯字幕或静音）")

    missing_analysis: list[str] = []
    if not transcript_text:
        missing_analysis.append("transcript")
    if not keyframe_paths:
        missing_analysis.append("keyframes")
    if all(item["shot_type"] is None for item in shots_list):
        missing_analysis.append("shot_type_classification")

    word_count = len(transcript_text.split()) if transcript_text else 0
    shots_per_second = round(n_shots / dur, 3) if dur else 0.0
    words_per_second = round(word_count / dur, 3) if dur and word_count else None
    confidence_values = [item["confidence"] for item in shots_list]
    overall_confidence = (
        round(sum(confidence_values) / len(confidence_values), 3)
        if confidence_values else 0.0
    )

    # 禁止复制的内容（根据模式设置）
    do_not_copy = [
        "原视频文案、台词、观点",
        "原视频具体案例、数据、结论",
        "原视频标题和封面",
    ]

    recipe: dict[str, Any] = {
        "episode_id": episode_id,
        "source_asset_id": source_asset_id,
        "duration": round(float(probe.get("duration") or 0.001), 3),
        "width": int(probe.get("width") or 1),
        "height": int(probe.get("height") or 1),
        "fps": round(float(probe.get("fps") or 30), 3),
        "has_audio": probe.get("has_audio"),
        "shots": shots_list,
        "hook": shots_list[0].get("transcript") if shots_list else None,
        "narrative_segments": [s["shot_id"] for s in shots_list],
        "ending_style": shots_list[-1].get("transcript") if len(shots_list) > 1 else None,
        "transferable_rules": transferable,
        "do_not_copy": do_not_copy,
        "structure": {
            "opening": shots_list[0]["shot_id"] if shots_list else None,
            "body": [item["shot_id"] for item in shots_list[1:-1]],
            "ending": shots_list[-1]["shot_id"] if len(shots_list) > 1 else None,
        },
        "information_density": {
            "shots_per_second": shots_per_second,
            "words_per_second": words_per_second,
        },
        "missing_analysis": missing_analysis,
        "overall_confidence": overall_confidence,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    return recipe


def save_recipe(
    episode_dir: Path,
    recipe: dict[str, Any],
    *,
    output_path: Path | None = None,
) -> Path:
    """校验并保存 reference-recipe.json，返回路径。"""
    # Schema 校验
    try:
        schema = _load_schema()
        jsonschema.Draft7Validator(
            schema,
            format_checker=jsonschema.FormatChecker(),
        ).validate(recipe)
    except jsonschema.ValidationError as exc:
        raise ValueError(f"reference-recipe Schema 校验失败: {exc.message}") from exc

    out = output_path or recipe_path(episode_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(recipe, fh, ensure_ascii=False, indent=2)
        tmp.replace(out)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise OSError(f"recipe 写入失败: {exc}") from exc
    return out


def load_recipe(episode_dir: Path) -> dict[str, Any]:
    """加载 reference-recipe.json（含 Schema 校验）。"""
    p = recipe_path(episode_dir)
    if not p.exists():
        raise FileNotFoundError(f"reference-recipe.json 不存在: {p}")
    with p.open(encoding="utf-8") as fh:
        data = json.load(fh)
    schema = _load_schema()
    jsonschema.validate(data, schema)
    return data
