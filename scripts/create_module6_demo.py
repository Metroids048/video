"""scripts/create_module6_demo.py — 创建 EP-M6-DEMO fixture。

用途：为模块6验收生成最小可运行 Demo Episode。
"""
from __future__ import annotations

import json
import shutil
import argparse
from datetime import datetime, timezone
from pathlib import Path


def create_demo(
    root: Path, *, force: bool = False, episode_id: str = "EP-M6-DEMO",
) -> Path:
    """创建 EP-M6-DEMO，返回 episode 目录。"""
    ep_dir = root / "episodes" / "active" / episode_id
    if ep_dir.exists():
        if not force:
            raise FileExistsError(
                f"{ep_dir} 已存在；原始输入受保护。确认重建时请使用 --force",
            )
        shutil.rmtree(ep_dir)

    # 目录骨架
    from avs.paths import create_episode_skeleton
    ep_dir.mkdir(parents=True)
    create_episode_skeleton(ep_dir)

    # episode.json
    from avs.models.episode import EpisodeModel
    model = EpisodeModel.create(episode_id, mode="ORIGINAL", platforms=["douyin"])
    model.transition("INGESTED")
    model.complete_stage("ingest")
    model.transition("CONTENT_READY")
    model.complete_stage("content")
    model.transition("ASSETS_READY")
    model.complete_stage("assets")
    model.save(ep_dir / "episode.json")

    generated_at = datetime.now(tz=timezone.utc).isoformat()
    (ep_dir / "input" / "idea.md").write_text(
        "这是一个只用于模块六渲染的本地示例。", encoding="utf-8",
    )
    # script.json（最小但可追溯）
    script = {
        "episode_id": episode_id,
        "total_duration_estimate": 9.0,
        "segments": [
            {
                "segment_id": "seg001", "text": "模块六示例开场",
                "purpose": "hook", "target_duration": 3.0,
                "visual_hint": "标题占位卡", "source_refs": ["input/idea.md"],
                "status": "draft", "notes": None,
            },
            {
                "segment_id": "seg002", "text": "模块六示例主体",
                "purpose": "body", "target_duration": 4.0,
                "visual_hint": "主体占位卡", "source_refs": ["input/idea.md"],
                "status": "draft", "notes": None,
            },
            {
                "segment_id": "seg003", "text": "模块六示例结尾",
                "purpose": "cta", "target_duration": 2.0,
                "visual_hint": "结尾占位卡", "source_refs": ["input/idea.md"],
                "status": "draft", "notes": None,
            },
        ],
        "generated_at": generated_at,
    }
    (ep_dir / "work" / "content" / "script.json").write_text(
        json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    # storyboard.json（canonical）
    storyboard = {
        "episode_id": episode_id,
        "shots": [
            {
                "scene_id": "scene001", "script_segment_ids": ["seg001"],
                "duration": 3.0, "visual_type": "placeholder", "asset_ids": [],
                "caption": "模块六示例开场", "motion_template": None,
                "missing_assets": ["需要标题素材"], "notes": None,
            },
            {
                "scene_id": "scene002", "script_segment_ids": ["seg002"],
                "duration": 4.0, "visual_type": "placeholder", "asset_ids": [],
                "caption": "模块六示例主体", "motion_template": None,
                "missing_assets": ["需要主体素材"], "notes": None,
            },
            {
                "scene_id": "scene003", "script_segment_ids": ["seg003"],
                "duration": 2.0, "visual_type": "placeholder", "asset_ids": [],
                "caption": "模块六示例结尾", "motion_template": None,
                "missing_assets": ["需要结尾素材"], "notes": None,
            },
        ],
        "asset_gaps": ["scene001", "scene002", "scene003"],
        "generated_at": generated_at,
    }
    (ep_dir / "work" / "content" / "storyboard.json").write_text(
        json.dumps(storyboard, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # asset-manifest.json（空）
    manifest = {
        "episode_id": episode_id,
        "assets": [],
        "generated_at": generated_at,
    }
    (ep_dir / "work" / "asset-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"✓ {episode_id} 已创建: {ep_dir}")
    print("  可运行:")
    print(f"    python -m avs timeline build {episode_id}")
    print(f"    python -m avs timeline validate {episode_id}")
    print(f"    python -m avs subtitles build {episode_id}")
    print(f"    python -m avs render rough {episode_id}")
    return ep_dir


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
    parser = argparse.ArgumentParser(description="创建模块 6 本地验收 Episode")
    parser.add_argument("--force", action="store_true", help="覆盖已有 EP-M6-DEMO")
    args = parser.parse_args()
    root = Path(__file__).parents[1]
    try:
        create_demo(root, force=args.force)
    except FileExistsError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
