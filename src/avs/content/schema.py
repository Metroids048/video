"""src/avs/content/schema.py — Script/Storyboard Schema 校验。"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import jsonschema

from avs.ingest.manifest import load_manifest

log = logging.getLogger(__name__)

_SCRIPT_SCHEMA = Path(__file__).resolve().parents[3] / "schemas" / "script.schema.json"
_STORYBOARD_SCHEMA = Path(__file__).resolve().parents[3] / "schemas" / "storyboard.schema.json"


class ContentValidationError(ValueError):
    """跨 Script、Storyboard、素材清单的语义校验失败。"""


def _load_schema(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def validate_script(data: dict[str, Any]) -> None:
    """校验 script.json；失败时抛出 jsonschema.ValidationError。"""
    schema = _load_schema(_SCRIPT_SCHEMA)
    jsonschema.Draft7Validator(
        schema, format_checker=jsonschema.FormatChecker(),
    ).validate(data)


def validate_storyboard(data: dict[str, Any]) -> None:
    """校验 storyboard.json；失败时抛出 jsonschema.ValidationError。"""
    schema = _load_schema(_STORYBOARD_SCHEMA)
    jsonschema.Draft7Validator(
        schema, format_checker=jsonschema.FormatChecker(),
    ).validate(data)


def validate_content_bundle(episode_dir: Path) -> None:
    """校验内容产物的引用、映射和缺失素材声明。"""
    script = load_script(episode_dir)
    storyboard = load_storyboard(episode_dir)
    manifest = load_manifest(episode_dir)
    errors: list[str] = []

    if script["episode_id"] != episode_dir.name or storyboard["episode_id"] != episode_dir.name:
        errors.append("episode_id 与 Episode 目录不一致")

    segment_ids = [segment["segment_id"] for segment in script["segments"]]
    if len(segment_ids) != len(set(segment_ids)):
        errors.append("Script Segment ID 重复")
    for segment in script["segments"]:
        for source_ref in segment["source_refs"]:
            if "://" in source_ref:
                links = "\n".join(
                    path.read_text(encoding="utf-8", errors="replace")
                    for path in (episode_dir / "input").glob("**/links.txt")
                )
                if source_ref not in links:
                    errors.append(f"source_ref 链接未出现在 links.txt: {source_ref}")
                continue
            source_path = source_ref.split("#", 1)[0]
            path = Path(source_path)
            if path.is_absolute() or ".." in path.parts:
                errors.append(f"source_ref 非法路径: {source_ref}")
                continue
            if not (episode_dir / path).is_file():
                errors.append(f"source_ref 不存在: {source_ref}")

    available_assets = {
        asset["asset_id"]
        for asset in manifest["assets"]
        if asset["status"] == "ok"
        and asset.get("working_path")
        and (episode_dir / asset["working_path"]).is_file()
    }
    scene_ids: list[str] = []
    actual_gaps: set[str] = set()
    for scene in storyboard["shots"]:
        scene_id = scene["scene_id"]
        scene_ids.append(scene_id)
        unknown_segments = set(scene["script_segment_ids"]) - set(segment_ids)
        if unknown_segments:
            errors.append(
                f"{scene_id}: 未知 Script Segment: {', '.join(sorted(unknown_segments))}"
            )
        unknown_assets = set(scene["asset_ids"]) - available_assets
        if unknown_assets:
            errors.append(f"{scene_id}: 未知或不可用 asset_id: {', '.join(sorted(unknown_assets))}")
        if scene["missing_assets"]:
            actual_gaps.add(scene_id)
        if (
            scene["visual_type"] in {"image", "video", "screen_recording", "b_roll"}
            and not scene["asset_ids"]
            and not scene["missing_assets"]
        ):
            errors.append(f"{scene_id}: 缺少 asset_ids 且未声明 missing_assets")

    if len(scene_ids) != len(set(scene_ids)):
        errors.append("Storyboard scene_id 重复")
    declared_gaps = set(storyboard.get("asset_gaps", []))
    if declared_gaps != actual_gaps:
        errors.append("asset_gaps 与各 Scene 的 missing_assets 不一致")

    missing_path = episode_dir / "work" / "content" / "missing-assets.md"
    if not missing_path.is_file():
        errors.append("missing-assets.md 缺失")
    else:
        missing_text = missing_path.read_text(encoding="utf-8")
        for scene_id in actual_gaps:
            if scene_id not in missing_text:
                errors.append(f"missing-assets.md 未列出 {scene_id}")

    for filename in ("brief.md", "script.md", "storyboard.md"):
        if not (episode_dir / "work" / "content" / filename).is_file():
            errors.append(f"{filename} 缺失")
    if errors:
        raise ContentValidationError("; ".join(errors))


def script_path(episode_dir: Path) -> Path:
    return episode_dir / "work" / "content" / "script.json"


def storyboard_path(episode_dir: Path) -> Path:
    return episode_dir / "work" / "content" / "storyboard.json"


def load_script(episode_dir: Path) -> dict[str, Any]:
    """加载并校验 script.json。"""
    p = script_path(episode_dir)
    if not p.exists():
        raise FileNotFoundError(f"script.json 不存在: {p}")
    with p.open(encoding="utf-8") as fh:
        data = json.load(fh)
    validate_script(data)
    return data


def load_storyboard(episode_dir: Path) -> dict[str, Any]:
    """加载并校验 storyboard.json。"""
    p = storyboard_path(episode_dir)
    if not p.exists():
        raise FileNotFoundError(f"storyboard.json 不存在: {p}")
    with p.open(encoding="utf-8") as fh:
        data = json.load(fh)
    validate_storyboard(data)
    return data


def save_script(episode_dir: Path, data: dict[str, Any]) -> Path:
    """校验并保存 script.json。"""
    validate_script(data)
    p = script_path(episode_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        tmp.replace(p)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise OSError(f"script.json 写入失败: {exc}") from exc
    return p


def save_storyboard(episode_dir: Path, data: dict[str, Any]) -> Path:
    """校验并保存 storyboard.json。"""
    validate_storyboard(data)
    p = storyboard_path(episode_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        tmp.replace(p)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise OSError(f"storyboard.json 写入失败: {exc}") from exc
    return p
