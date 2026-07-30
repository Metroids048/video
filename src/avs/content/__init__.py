"""src/avs/content/__init__.py — 模块5主入口：内容生成委托给Agent。

CLI 只负责初始化目录、Schema校验和状态推进。
实际文案生成由 Agent + Skills 完成（不在 Python 中硬编码大模型调用）。
"""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def init_content_workspace(episode_dir: Path) -> Path:
    """初始化 work/content/ 目录，返回路径。"""
    content_dir = episode_dir / "work" / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    # 创建输出目录
    (content_dir / "drafts").mkdir(exist_ok=True)

    # 创建 brief.md 模板（如果不存在）
    brief_path = content_dir / "brief.md"
    if not brief_path.exists():
        brief_path.write_text(
            "# Content Brief\n\n"
            "## 输入素材清点\n"
            "- [ ] 参考视频分析\n"
            "- [ ] 用户提供的文本/notes\n"
            "- [ ] links.txt\n\n"
            "## 核心观点\n"
            "（待Agent填写）\n\n"
            "## 目标受众\n"
            "（待Agent填写）\n\n"
            "## 视频结构\n"
            "（待Agent填写）\n",
            encoding="utf-8"
        )

    log.info("内容工作区初始化: %s", content_dir)
    return content_dir


def check_prerequisites(episode_dir: Path) -> dict[str, bool]:
    """检查内容生成前置条件，返回可用资源字典。"""
    from avs.ingest.manifest import manifest_path
    from avs.reference.recipe import recipe_path

    return {
        "has_asset_manifest": manifest_path(episode_dir).exists(),
        "has_reference_recipe": recipe_path(episode_dir).exists(),
        "has_input_text": any(
            path.is_file()
            for pattern in ("**/*.txt", "**/*.md")
            for path in (episode_dir / "input").glob(pattern)
        ),
        "has_input_links": (episode_dir / "input" / "links.txt").exists(),
    }


def get_content_status(episode_dir: Path) -> dict[str, bool]:
    """检查内容产物状态。"""
    from avs.content.schema import script_path, storyboard_path

    content_dir = episode_dir / "work" / "content"
    return {
        "brief_exists": (content_dir / "brief.md").exists(),
        "script_json_exists": script_path(episode_dir).exists(),
        "storyboard_json_exists": storyboard_path(episode_dir).exists(),
        "missing_assets_exists": (content_dir / "missing-assets.md").exists(),
    }
