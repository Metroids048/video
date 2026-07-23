"""src/avs/timeline/validate.py — timeline.json Schema + 语义校验。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema


@dataclass
class ValidationIssue:
    level: str    # "error" | "warning"
    message: str


class TimelineValidationError(Exception):
    """时间线 Schema 或语义校验失败。"""


def _load_schema(schema_path: Path) -> dict[str, Any]:
    if not schema_path.exists():
        raise TimelineValidationError(f"Schema 文件缺失: {schema_path}")
    with schema_path.open(encoding="utf-8") as fh:
        return json.load(fh)


def validate_timeline(
    timeline_path: Path,
    schema_path: Path | None = None,
) -> list[ValidationIssue]:
    """校验 timeline.json；返回 issue 列表（空=通过）。

    错误 (error) 表示不可渲染；警告 (warning) 表示可渲染但有问题。
    """
    if not timeline_path.exists():
        raise TimelineValidationError(f"timeline.json 不存在: {timeline_path}")

    with timeline_path.open(encoding="utf-8") as fh:
        data = json.load(fh)

    # 确定 schema 路径
    if schema_path is None:
        # 从 timeline 文件向上查找项目根
        root = timeline_path
        for _ in range(10):
            root = root.parent
            if (root / "schemas" / "timeline.schema.json").exists():
                schema_path = root / "schemas" / "timeline.schema.json"
                break
    if schema_path is None or not schema_path.exists():
        raise TimelineValidationError("无法定位 schemas/timeline.schema.json")

    issues: list[ValidationIssue] = []

    # ── JSON Schema 校验 ────────────────────────────────────────────────
    try:
        schema = _load_schema(schema_path)
        jsonschema.Draft7Validator(
            schema, format_checker=jsonschema.FormatChecker(),
        ).validate(data)
    except jsonschema.ValidationError as exc:
        raise TimelineValidationError(f"Schema 校验失败: {exc.message}") from exc

    # ── 语义校验 ─────────────────────────────────────────────────────────

    canvas = data.get("canvas", {})
    w, h, fps = canvas.get("width", 0), canvas.get("height", 0), canvas.get("fps", 0)
    if w != 1080 or h != 1920:
        issues.append(ValidationIssue("warning", f"画布非标准尺寸: {w}×{h}（期望 1080×1920）"))
    if fps not in (30, 30.0, 29.97):
        issues.append(ValidationIssue("warning", f"帧率非标准: {fps}（期望 30）"))

    total_dur = data.get("total_duration")
    if total_dur is not None and total_dur <= 0:
        issues.append(ValidationIssue("error", f"total_duration 必须 > 0，实际: {total_dur}"))

    # 轨道和 clip 校验
    seen_clip_ids: set[str] = set()
    for track in data.get("tracks", []):
        tid = track.get("track_id", "?")
        for clip in track.get("clips", []):
            cid = clip.get("clip_id", "?")

            # clip_id 唯一性
            if cid in seen_clip_ids:
                issues.append(ValidationIssue("error", f"重复 clip_id: {cid}"))
            seen_clip_ids.add(cid)

            start = clip.get("start", 0)
            dur = clip.get("duration", 0)

            if dur <= 0:
                issues.append(ValidationIssue("error", f"[{tid}/{cid}] duration 必须 > 0"))

            asset_ref = clip.get("asset_ref")
            if asset_ref:
                ref = Path(asset_ref)
                if ref.is_absolute() or ".." in ref.parts:
                    issues.append(ValidationIssue("error", f"[{tid}/{cid}] asset_ref 非法路径"))
                elif not ref.as_posix().startswith("work/prepared/"):
                    issues.append(ValidationIssue(
                        "error", f"[{tid}/{cid}] asset_ref 必须引用 work/prepared 工作副本",
                    ))
                else:
                    episode_dir = timeline_path.parent.parent
                    if not (episode_dir / ref).is_file():
                        issues.append(ValidationIssue(
                            "error", f"[{tid}/{cid}] asset_ref 文件不存在: {asset_ref}",
                        ))

            # 字幕越界检测
            if track.get("kind") == "caption":
                if total_dur and (start + dur) > total_dur + 0.1:
                    issues.append(ValidationIssue(
                        "error",
                        f"[{tid}/{cid}] 字幕越界: end={start+dur:.3f}s > total={total_dur}s"
                    ))

    # 检查 video track 存在
    kinds = {t.get("kind") for t in data.get("tracks", [])}
    if "video" not in kinds:
        issues.append(ValidationIssue("error", "没有 video 轨道"))

    return issues
