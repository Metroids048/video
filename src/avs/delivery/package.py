"""src/avs/delivery/package.py — 生成可编辑交付包。"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from avs.models.episode import EpisodeModel


def run_delivery(ep_dir: Path, model: EpisodeModel, *, force: bool = False) -> dict:
    """生成交付包，返回 delivery-manifest.json 内容。

    交付包内容：
    - renders/*.mp4
    - delivery/captions.srt
    - work/timeline.json + timeline.csv
    - work/content/*.json（script/storyboard）
    - delivery/assets-used/（实际使用的素材副本）
    - delivery/motion-graphics/（HyperFrames 输出）
    - delivery/edit-notes.md（编辑指南）
    - delivery/qa-report.md
    - delivery/publish/*.md（平台文案）
    - delivery/delivery-manifest.json（清单）
    """
    manifest_path = ep_dir / "delivery" / "delivery-manifest.json"
    if manifest_path.exists() and not force:
        # 幂等：已存在时直接返回
        with manifest_path.open(encoding="utf-8") as fh:
            return json.load(fh)

    delivery_dir = ep_dir / "delivery"
    delivery_dir.mkdir(parents=True, exist_ok=True)

    files: list[dict] = []

    # ── 核心产物 ──────────────────────────────────────────────────────
    for src in [
        ep_dir / "renders" / "preview-clean.mp4",
        ep_dir / "renders" / "preview-with-captions.mp4",
    ]:
        if src.exists():
            files.append({
                "name": src.name,
                "path": str(src.relative_to(ep_dir)),
                "required": True,
                "size_bytes": src.stat().st_size,
                "sha256": _sha256(src),
            })

    # ── 字幕 ──────────────────────────────────────────────────────────
    srt_src = ep_dir / "work" / "captions.srt"
    srt_dst = delivery_dir / "captions.srt"
    if srt_src.exists():
        shutil.copy2(str(srt_src), str(srt_dst))
        files.append({
            "name": "captions.srt",
            "path": str(srt_dst.relative_to(ep_dir)),
            "required": False,
            "size_bytes": srt_dst.stat().st_size,
            "sha256": None,
        })

    # ── 时间线 ────────────────────────────────────────────────────────
    for fname in ("timeline.json", "timeline.csv"):
        src = ep_dir / "work" / fname
        if src.exists():
            files.append({
                "name": fname,
                "path": str(src.relative_to(ep_dir)),
                "required": False,
                "size_bytes": src.stat().st_size,
                "sha256": None,
            })

    # ── 编辑说明（草稿）──────────────────────────────────────────────
    edit_notes_path = delivery_dir / "edit-notes.md"
    if not edit_notes_path.exists():
        _write_edit_notes(ep_dir, edit_notes_path)
    files.append({
        "name": "edit-notes.md",
        "path": str(edit_notes_path.relative_to(ep_dir)),
        "required": False,
        "size_bytes": edit_notes_path.stat().st_size,
        "sha256": None,
    })

    # ── 平台文案（草稿）──────────────────────────────────────────────
    publish_dir = delivery_dir / "publish"
    publish_dir.mkdir(exist_ok=True)
    for platform in model.to_dict().get("platforms", ["douyin", "xiaohongshu"]):
        pub_file = publish_dir / f"{platform}.md"
        if not pub_file.exists():
            _write_publish_copy(platform, model, pub_file)
        files.append({
            "name": f"publish/{platform}.md",
            "path": str(pub_file.relative_to(ep_dir)),
            "required": False,
            "size_bytes": pub_file.stat().st_size,
            "sha256": None,
        })

    # ── 生成清单 ──────────────────────────────────────────────────────
    manifest = {
        "episode_id": model.id,
        "publishable": model.publishable,
        "platforms": model.to_dict().get("platforms", []),
        "files": files,
        "edit_notes_path": str(edit_notes_path.relative_to(ep_dir)),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    return manifest


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_edit_notes(ep_dir: Path, output: Path) -> None:
    """生成编辑说明草稿（列出占位卡、修改建议）。"""
    lines = [
        f"# 编辑说明",
        "",
        "本文件列出粗剪中需要人工修改的地方。",
        "",
        "## 占位卡",
        "",
    ]
    timeline_path = ep_dir / "work" / "timeline.json"
    if timeline_path.exists():
        with timeline_path.open(encoding="utf-8") as fh:
            tl = json.load(fh)
        placeholders: list[str] = []
        for track in tl.get("tracks", []):
            for clip in track.get("clips", []):
                if clip.get("style", {}).get("placeholder"):
                    text = clip.get("text", "")
                    placeholders.append(f"- **{clip['clip_id']}** ({clip['start']:.1f}s–{clip['start']+clip['duration']:.1f}s): {text}")
        if placeholders:
            lines.extend(placeholders)
        else:
            lines.append("（无占位卡）")
    else:
        lines.append("（timeline.json 不存在）")

    lines.extend([
        "",
        "## 建议修改",
        "",
        "- 字幕时间调整（根据实际语速）",
        "- BGM 音量平衡",
        "- 转场过渡优化",
        "",
    ])
    output.write_text("\n".join(lines), encoding="utf-8")


def _write_publish_copy(platform: str, model: EpisodeModel, output: Path) -> None:
    """生成平台发布文案草稿。"""
    data = model.to_dict()
    title = data.get("title") or f"{model.id} 视频"
    lines = [
        f"# {platform.capitalize()} 发布文案",
        "",
        f"**标题**: {title}",
        "",
        "**正文**:",
        "",
        "（此处填写发布正文）",
        "",
        "**话题**: #示例话题",
        "",
        "**封面**: （从 renders/ 中选取关键帧）",
        "",
    ]
    if not model.publishable:
        lines.insert(2, "")
        lines.insert(3, "⚠️ **不可发布** — 此 Episode 使用 REFERENCE_CLONE 模式，仅供内部学习。")
        lines.insert(4, "")
    output.write_text("\n".join(lines), encoding="utf-8")
