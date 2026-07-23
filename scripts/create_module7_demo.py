"""Create the local module 7 Episode with all three HyperFrames templates."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from create_module6_demo import create_demo  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="创建模块 7 HyperFrames 验收 Episode")
    parser.add_argument("--force", action="store_true", help="覆盖已有 EP-M7-DEMO")
    args = parser.parse_args()
    ep_dir = create_demo(ROOT, force=args.force, episode_id="EP-M7-DEMO")
    storyboard_path = ep_dir / "work" / "content" / "storyboard.json"
    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
    templates = ["HookTitle", "InfoCard", "EndCard"]
    for shot, template in zip(storyboard["shots"], templates):
        shot["motion_template"] = template
    storyboard_path.write_text(
        json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print(f"✓ EP-M7-DEMO 已创建: {ep_dir}")
    print("  下一步: avs timeline build --force EP-M7-DEMO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
