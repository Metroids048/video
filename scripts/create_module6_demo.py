"""scripts/create_module6_demo.py — 创建 EP-M6-DEMO fixture。

用途：为模块6验收生成最小可运行 Demo Episode。
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path


def create_demo(root: Path) -> Path:
    """创建 EP-M6-DEMO，返回 episode 目录。"""
    ep_dir = root / "episodes" / "active" / "EP-M6-DEMO"
    if ep_dir.exists():
        shutil.rmtree(ep_dir)

    # 目录骨架
    from avs.paths import create_episode_skeleton
    ep_dir.mkdir(parents=True)
    create_episode_skeleton(ep_dir)

    # episode.json
    from avs.models.episode import EpisodeModel
    model = EpisodeModel.create("EP-M6-DEMO", mode="ORIGINAL", platforms=["douyin"])
    model.transition("INGESTED")
    model.transition("CONTENT_READY")
    model.save(ep_dir / "episode.json")

    # storyboard.json（最小）
    storyboard = {
        "episode_id": "EP-M6-DEMO",
        "shots": [
            {
                "shot_id": "s001",
                "order": 1,
                "description": "标题画面",
                "duration_estimate": 3.0,
                "gap": True,
                "gap_note": "需要标题素材",
            },
            {
                "shot_id": "s002",
                "order": 2,
                "description": "主体内容",
                "duration_estimate": 4.0,
                "gap": True,
                "gap_note": "需要主体素材",
            },
            {
                "shot_id": "s003",
                "order": 3,
                "description": "结尾",
                "duration_estimate": 2.0,
                "gap": True,
                "gap_note": "需要结尾素材",
            },
        ],
        "asset_gaps": ["s001", "s002", "s003"],
        "generated_at": "2026-07-20T15:00:00Z",
    }
    (ep_dir / "work" / "content" / "storyboard.json").write_text(
        json.dumps(storyboard, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # asset-manifest.json（空）
    manifest = {
        "episode_id": "EP-M6-DEMO",
        "assets": [],
        "generated_at": "2026-07-20T15:00:00Z",
    }
    (ep_dir / "work" / "asset-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"✓ EP-M6-DEMO 已创建: {ep_dir}")
    print("  可运行:")
    print("    python -m avs timeline build EP-M6-DEMO")
    print("    python -m avs timeline validate EP-M6-DEMO")
    print("    python -m avs subtitles build EP-M6-DEMO")
    print("    python -m avs render rough EP-M6-DEMO")
    return ep_dir


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
    root = Path(__file__).parents[1]
    create_demo(root)
