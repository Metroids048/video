"""一键成片示例：从素材到成品视频全自动。

场景：用户有 N 个 vlog 素材 + 1 个 BGM，想做一个完整 vlog。

用法：
    python examples/auto-edit-demo.py --project my_vlog \\
        --inputs /path/to/clips/ --bgm /path/to/bgm.mp3
"""
import argparse
import glob
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from cut.jianying.draft import Draft
from cut.jianying import materials, auto_edit


def find_media_files(input_dir):
    exts = ("*.mp4", "*.mov", "*.mkv", "*.avi", "*.flv", "*.webm", "*.m4v")
    files = []
    for ext in exts:
        files.extend(glob.glob(os.path.join(input_dir, ext)))
        files.extend(glob.glob(os.path.join(input_dir, "**", ext), recursive=True))
    return sorted(set(files))


def main():
    parser = argparse.ArgumentParser(description="一键成片示例")
    parser.add_argument("--project", required=True, help="剪映项目名")
    parser.add_argument("--inputs", required=True, help="视频文件目录")
    parser.add_argument("--bgm", help="BGM 音频文件路径")
    parser.add_argument("--template", default="vlog",
                        choices=["tutorial","review","vlog","knowledge","drama",
                                 "comparison","emotional","beat_sync"])
    parser.add_argument("--texts", help="每个 phase 文字，用 | 分隔")
    parser.add_argument("--color-preset", help="覆盖模板调色")
    parser.add_argument("--beat-sync", action="store_true", help="启用节拍卡点")
    parser.add_argument("--subtitle-engine", default="mock",
                        choices=["mock","whisper","online"])
    args = parser.parse_args()

    print(f"[1/4] 扫描素材: {args.inputs}")
    files = find_media_files(args.inputs)
    if not files:
        print("未找到视频文件", file=sys.stderr)
        sys.exit(1)
    print(f"      找到 {len(files)} 个文件")

    print(f"[2/4] 打开剪映项目: {args.project}")
    try:
        draft = Draft.open(project_name=args.project)
    except Exception:
        print("项目不存在，请在剪映中先创建一个空项目")
        sys.exit(1)

    print(f"[3/4] 导入素材")
    mat_ids = []
    for i, f in enumerate(files):
        try:
            mid = materials.import_video(draft, f, alias=f"clip_{i+1}")
            if not draft.find_material(mid).get("duration"):
                draft.find_material(mid)["duration"] = 8_000_000
            mat_ids.append(mid)
            print(f"      ({i+1}/{len(files)}) {os.path.basename(f)}")
        except Exception as e:
            print(f"      失败: {e}")

    bgm_mid = None
    if args.bgm:
        try:
            bgm_mid = materials.import_audio(draft, args.bgm, alias="bgm")
            if not draft.find_material(bgm_mid).get("duration"):
                draft.find_material(bgm_mid)["duration"] = 60_000_000
        except Exception as e:
            print(f"      BGM 导入失败: {e}")

    print(f"[4/4] 一键成片 (template={args.template})")
    texts = args.texts.split("|") if args.texts else None

    result = auto_edit.auto_edit(
        draft, mat_ids,
        bgm_material_id=bgm_mid,
        template=args.template,
        texts=texts,
        auto_subtitle=True,
        auto_color=True,
        auto_transition=True,
        beat_sync=args.beat_sync,
        color_preset=args.color_preset,
        subtitle_engine=args.subtitle_engine,
    )

    print(f"\n结果:")
    print(f"  总时长: {result['total_duration_hms']}")
    print(f"  步骤: {len(result['steps'])}")
    for step in result["steps"]:
        print(f"    ✓ {step['step']}: {step.get('status', 'ok')}")
    if result["errors"]:
        print(f"  警告: {len(result['errors'])} 个")
        for e in result["errors"]:
            print(f"    ! {e['step']}: {e['error']}")

    draft.save()
    print(f"\n✓ 完成。请在剪映中重新打开项目查看。")


if __name__ == "__main__":
    main()
