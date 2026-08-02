"""批量裁切示例：导入多个视频，按场景切分，加转场，导出。

场景：用户有 10 个短视频素材，想批量处理：
1. 全部导入剪映
2. 每 5 秒切一刀
3. 相邻片段间加 fade 转场
4. 导出为单个 mp4

用法：
    python examples/batch-cut.py --project batch_test --inputs /path/to/dir/

依赖：
    pip install -r requirements.txt
    系统安装 ffmpeg（用于素材探测）
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
from pathlib import Path

# 把 scripts 目录加到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from cut.jianying.draft import Draft
from cut.jianying import materials, segments, effects, export as E


def find_media_files(input_dir: str) -> list:
    """扫描目录下所有视频文件。"""
    exts = ("*.mp4", "*.mov", "*.mkv", "*.avi", "*.flv", "*.webm", "*.m4v")
    files = []
    for ext in exts:
        files.extend(glob.glob(os.path.join(input_dir, ext)))
        files.extend(glob.glob(os.path.join(input_dir, "**", ext), recursive=True))
    return sorted(set(files))


def batch_cut(project_name: str, input_dir: str, split_interval_us: int = 5_000_000,
              transition_preset: str = "fade", output_path: str = "output.mp4"):
    """批量裁切主流程。"""
    print(f"[1/5] 扫描素材: {input_dir}")
    files = find_media_files(input_dir)
    if not files:
        print("未找到视频文件", file=sys.stderr)
        sys.exit(1)
    print(f"  找到 {len(files)} 个文件")

    # 打开或创建项目
    print(f"[2/5] 打开剪映项目: {project_name}")
    try:
        draft = Draft.open(project_name=project_name)
        print(f"  已打开现有项目，时长 {draft.duration_hms}")
    except Exception:
        print("  项目不存在，请在剪映中先创建一个空项目")
        sys.exit(1)

    # 导入并追加到时间轴
    print(f"[3/5] 导入素材并追加到时间轴")
    last_end_us = draft.duration
    for i, f in enumerate(files):
        print(f"  ({i+1}/{len(files)}) {os.path.basename(f)}")
        try:
            mid = materials.import_video(draft, f, alias=f"clip_{i+1}")
            sid = materials.add_video_segment(
                draft, mid, start_us=last_end_us, duration_us=None,
            )
            # 重新读取刚加的 segment 拿到时长
            seg = draft.get_segment_raw(sid)
            dur = seg["target_timerange"]["duration"]
            last_end_us += dur
        except Exception as e:
            print(f"    失败: {e}")

    # 每 5 秒切一刀
    print(f"[4/5] 每 {split_interval_us // 1_000_000}s 切一刀")
    for track in draft.video_tracks:
        for seg in list(track.segments):
            # 在 seg 内部每 split_interval_us 切一刀
            n = seg.duration_us // split_interval_us
            for k in range(1, int(n)):
                at = seg.start_us + k * split_interval_us
                if seg.start_us < at < seg.end_us:
                    try:
                        segments.split_segment(draft, seg, at_us=at)
                    except Exception as e:
                        print(f"    切分失败 {at}: {e}")

    # 加转场
    print(f"[5/5] 加 {transition_preset} 转场")
    for track in draft.video_tracks:
        for i in range(len(track.segments) - 1):
            try:
                effects.add_transition_simple(
                    draft, track.id, i, preset=transition_preset,
                    duration_us=500_000,
                )
            except Exception as e:
                print(f"    转场失败 track={track.id} i={i}: {e}")

    # 保存
    print("保存 draft...")
    draft.save()
    print(f"✓ 完成。项目时长: {draft.duration_hms}")
    print(f"  请在剪映中重新打开项目查看。")
    print(f"  如需导出，运行:")
    print(f"    python -m cut.cli export --backend jianying --project {project_name} --output {output_path} --method ffmpeg")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="批量裁切示例")
    parser.add_argument("--project", required=True, help="剪映项目名")
    parser.add_argument("--inputs", required=True, help="视频文件目录")
    parser.add_argument("--split-interval", type=int, default=5, help="切分间隔（秒）")
    parser.add_argument("--transition", default="fade", help="转场预设")
    parser.add_argument("--output", default="output.mp4", help="输出文件名")
    args = parser.parse_args()

    batch_cut(
        project_name=args.project,
        input_dir=args.inputs,
        split_interval_us=args.split_interval * 1_000_000,
        transition_preset=args.transition,
        output_path=args.output,
    )
