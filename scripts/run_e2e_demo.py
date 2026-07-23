"""scripts/run_e2e_demo.py — E2E 全流程 Demo 验证脚本。

用途：模块9验收，演示完整流程（create→ingest→content→timeline→render→qa→deliver）。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list[str], label: str) -> int:
    """运行命令，打印标签，返回退出码。"""
    print(f"\n{'='*60}")
    print(f"[{label}]")
    print(f"{'='*60}")
    print(" ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"✗ {label} 失败 (exit {result.returncode})")
    else:
        print(f"✓ {label} 成功")
    return result.returncode


def main():
    root = Path(__file__).parents[1]
    ep_id = "EP-E2E-TEST"

    steps = [
        (["python", "-m", "avs", "episode", "create", ep_id], "创建 Episode"),
        (["python", "scripts/create_module6_demo.py"], "生成最小内容 fixture"),
        (["python", "-m", "avs", "timeline", "build", ep_id], "构建时间线"),
        (["python", "-m", "avs", "timeline", "validate", ep_id], "校验时间线"),
        (["python", "-m", "avs", "subtitles", "build", ep_id], "生成字幕"),
        (["python", "-m", "avs", "render", "rough", ep_id], "渲染粗剪"),
        (["python", "-m", "avs", "qa", ep_id], "QA 检查"),
        (["python", "-m", "avs", "deliver", ep_id], "生成交付包"),
        (["python", "-m", "avs", "episode", "status", ep_id], "最终状态"),
    ]

    failed: list[str] = []
    for cmd, label in steps:
        ret = run_cmd(cmd, label)
        if ret != 0:
            failed.append(label)

    print(f"\n{'='*60}")
    print("E2E Demo 完成")
    print(f"{'='*60}")
    if failed:
        print(f"✗ 失败步骤: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("✓ 全流程通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
