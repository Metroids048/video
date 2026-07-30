"""Build a self-contained editable delivery package."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from avs.delivery.manifest import file_record, sha256_file, validate_manifest
from avs.delivery.paths import safe_delivery_target
from avs.models.episode import EpisodeModel


def _copy_file(source: Path, target: Path, *, force: bool) -> Path:
    if not source.is_file():
        raise FileNotFoundError(f"交付所需文件不存在: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        if sha256_file(source) == sha256_file(target):
            return target
        if not force:
            raise FileExistsError(f"交付目标已有不同内容，请使用 --force: {target}")
    shutil.copy2(source, target)
    return target


def _write_text(path: Path, content: str, *, force: bool) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        if path.read_text(encoding="utf-8") == content:
            return path
        if not force:
            raise FileExistsError(f"交付目标已有不同内容，请使用 --force: {path}")
    path.write_text(content, encoding="utf-8")
    return path


def _qa_report(ep_dir: Path) -> dict[str, Any]:
    path = ep_dir / "delivery" / "qa-report.json"
    if not path.is_file():
        raise FileNotFoundError("缺少 delivery/qa-report.json，请先运行 avs qa")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("passed") is not True:
        raise ValueError("QA 报告未通过，不能生成交付包")
    return payload


def run_delivery(ep_dir: Path, model: EpisodeModel, *, force: bool = False) -> dict[str, Any]:
    """Copy all editable outputs into delivery/ and write a validated manifest."""
    if model.status not in {"QA_PASSED", "DELIVERY_READY"}:
        raise ValueError(f"当前状态 {model.status}，必须先达到 QA_PASSED")
    _qa_report(ep_dir)

    delivery_dir = ep_dir / "delivery"
    delivery_dir.mkdir(parents=True, exist_ok=True)
    files: list[tuple[Path, bool]] = []

    required_copies = (
        (ep_dir / "renders" / "preview-clean.mp4", Path("preview-clean.mp4")),
        (ep_dir / "renders" / "preview-with-captions.mp4", Path("preview-with-captions.mp4")),
        (ep_dir / "work" / "captions.srt", Path("captions.srt")),
        (ep_dir / "work" / "timeline.json", Path("timeline/timeline.json")),
        (ep_dir / "work" / "timeline.csv", Path("timeline/timeline.csv")),
    )
    for source, relative in required_copies:
        files.append((_copy_file(source, safe_delivery_target(ep_dir, relative), force=force), True))

    optional_copies = (
        (ep_dir / "renders" / "preview-with-motion.mp4", Path("preview-with-motion.mp4")),
        (ep_dir / "work" / "motion-manifest.json", Path("motion-manifest.json")),
        (ep_dir / "work" / "reference" / "reference-recipe.json", Path("reference/reference-recipe.json")),
        (ep_dir / "work" / "content" / "brief.md", Path("content/brief.md")),
        (ep_dir / "work" / "content" / "script.json", Path("content/script.json")),
        (ep_dir / "work" / "content" / "storyboard.json", Path("content/storyboard.json")),
        (ep_dir / "work" / "content" / "missing-assets.md", Path("content/missing-assets.md")),
    )
    for source, relative in optional_copies:
        if source.is_file():
            files.append((_copy_file(source, safe_delivery_target(ep_dir, relative), force=force), False))

    timeline = json.loads((ep_dir / "work" / "timeline.json").read_text(encoding="utf-8"))
    asset_refs = sorted({
        clip["asset_ref"]
        for track in timeline.get("tracks", [])
        for clip in track.get("clips", [])
        if clip.get("asset_ref")
    })
    for reference in asset_refs:
        source = ep_dir / Path(reference)
        prepared_root = (ep_dir / "work" / "prepared").resolve()
        relative_asset = source.resolve().relative_to(prepared_root)
        target = safe_delivery_target(ep_dir, Path("assets-used") / relative_asset)
        files.append((_copy_file(source, target, force=force), False))

    motion_dir = delivery_dir / "motion-graphics"
    if motion_dir.is_dir():
        files.extend((path, False) for path in sorted(motion_dir.rglob("*.mp4")) if path.is_file())

    for qa_relative in ("qa-report.json", "qa-report.md", "visual-review.md", "qa-contact-sheet.jpg"):
        path = delivery_dir / qa_relative
        if not path.is_file():
            raise FileNotFoundError(f"缺少 QA 交付文件: delivery/{qa_relative}")
        files.append((path, True))

    edit_notes = _write_text(
        delivery_dir / "edit-notes.md", _edit_notes(timeline, publishable=model.publishable), force=force,
    )
    files.append((edit_notes, True))

    if model.publishable:
        for platform in model.to_dict().get("platforms", []):
            publish_path = delivery_dir / "publish" / f"{platform}.md"
            files.append((_write_text(publish_path, _publish_copy(platform, model), force=force), False))

    unique_files = {path.resolve(): (path, required) for path, required in files}
    records = [
        file_record(ep_dir, path, required=required)
        for path, required in sorted(unique_files.values(), key=lambda item: item[0].as_posix())
    ]
    manifest: dict[str, Any] = {
        "episode_id": model.id,
        "publishable": model.publishable,
        "platforms": model.to_dict().get("platforms", []) if model.publishable else [],
        "files": records,
        "edit_notes_path": "delivery/edit-notes.md",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    validate_manifest(ep_dir, manifest)

    manifest_path = delivery_dir / "delivery-manifest.json"
    if manifest_path.is_file() and not force:
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        validate_manifest(ep_dir, existing)
        comparable_existing = {key: value for key, value in existing.items() if key != "generated_at"}
        comparable_new = {key: value for key, value in manifest.items() if key != "generated_at"}
        if comparable_existing == comparable_new:
            return existing
        raise FileExistsError("delivery-manifest.json 已存在且内容不同，请使用 --force")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def _edit_notes(timeline: dict[str, Any], *, publishable: bool) -> str:
    placeholders = [
        f"- {clip['clip_id']} ({clip['start']:.1f}s-{clip['start'] + clip['duration']:.1f}s): {clip.get('text') or '未命名占位卡'}"
        for track in timeline.get("tracks", [])
        for clip in track.get("clips", [])
        if (clip.get("style") or {}).get("placeholder")
    ]
    final_step = "- 人工确认平台文案后发布" if publishable else "- 本包仅供内部学习，不得公开发布"
    lines = ["# 编辑说明", "", "## 待补素材", "", *(placeholders or ["- 无"]), "", "## 发布前人工复核", "", "- 完整播放并检查画面、音量、字幕和事实", "- 替换全部占位卡", "- 在剪映等软件中完成最终调整", final_step, ""]
    return "\n".join(lines)


def _publish_copy(platform: str, model: EpisodeModel) -> str:
    title = model.to_dict().get("title") or f"{model.id} 视频"
    return "\n".join([
        f"# {platform} 发布文案草稿", "", f"标题: {title}", "", "正文:", "", "（发布前人工填写并核对事实）", "", "话题:", "", "（发布前人工选择）", "",
    ])
