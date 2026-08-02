"""双轨混剪示例：主视频 + 画中画，背景音乐自动 ducking。

场景：做一个教学视频，主轨是讲师画面，副轨是 PPT/演示画面，
背景音乐在讲师说话时自动降低音量（ducking）。

流程：
1. 导入主视频到 V1
2. 导入副视频到 V2（画中画，缩小到右下角）
3. 导入背景音乐到 A1
4. 提取主视频音频，识别"说话时段"
5. 给背景音乐加 ducking 关键帧（说话时降到 30%）

用法：
    python examples/multi-track.py --project multi_track_test \
        --main /path/to/lecturer.mp4 \
        --pip /path/to/ppt.mp4 \
        --bgm /path/to/bgm.mp3
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from cut.jianying.draft import Draft, _new_id
from cut.jianying import materials, segments, audio as A


def setup_multitrack(project_name: str, main_video: str, pip_video: str, bgm: str):
    """配置双轨混剪。"""
    print(f"[1/5] 打开项目: {project_name}")
    draft = Draft.open(project_name=project_name)
    print(f"  当前时长: {draft.duration_hms}")

    # 1. 导入素材
    print(f"[2/5] 导入素材")
    main_mid = materials.import_video(draft, main_video, alias="主视频")
    pip_mid = materials.import_video(draft, pip_video, alias="画中画")
    bgm_mid = materials.import_audio(draft, bgm, alias="背景音乐")

    # 2. 主视频放 V1
    print(f"[3/5] 主视频放 V1")
    main_sid = materials.add_video_segment(draft, main_mid, start_us=0)

    # 3. 画中画放 V2（需要新建轨道）
    print(f"[4/5] 画中画放 V2 (画中画)")
    vts = draft.video_tracks
    if len(vts) < 2:
        v2_id = draft.add_track("video")
    else:
        v2_id = vts[1].id

    pip_sid = materials.add_video_segment(
        draft, pip_mid, track_id=v2_id, start_us=0,
    )
    # 缩小画中画到 30%，放右下角
    pip_seg = draft.get_segment_raw(pip_sid)
    if pip_seg:
        clip = pip_seg.setdefault("clip", {})
        clip["scale"] = {"x": 0.3, "y": 0.3}
        clip["transform"] = {"x": 0.6, "y": 0.4}  # 右下

    # 4. 背景音乐放 A1
    print(f"[5/5] 背景音乐放 A1 + ducking")
    bgm_sid = materials.add_audio_segment(draft, bgm_mid, start_us=0, volume=0.4)

    # 假设主视频前 5s 是片头音乐（无人说话），5s 后开始说话
    # 给 bgm 加 ducking：5s 时降到 0.3，主视频结束时回到 0.4
    main_seg = draft.get_segment_raw(main_sid)
    if main_seg:
        main_dur = main_seg["target_timerange"]["duration"]
        # 模拟的"说话时段"列表（实际应从 ASR 或音量分析得到）
        speech_ranges = [
            (5_000_000, min(main_dur, 30_000_000)),
            (35_000_000, min(main_dur, 60_000_000)),
            (65_000_000, min(main_dur, 90_000_000)),
        ]
        # 找出主视频对应的 audio segment（如果有）
        # 简化：直接给 bgm 加关键帧
        from cut.jianying.effects import add_keyframe
        bgm_vol = 0.4
        ducked = 0.12  # 30% of 0.4

        cur = 0
        for vstart, vend in speech_ranges:
            if vstart > cur:
                add_keyframe(draft, bgm_sid, cur, bgm_vol, field="volume")
                add_keyframe(draft, bgm_sid, vstart - 200_000, bgm_vol, field="volume")
            add_keyframe(draft, bgm_sid, vstart, ducked, field="volume")
            add_keyframe(draft, bgm_sid, vend, ducked, field="volume")
            add_keyframe(draft, bgm_sid, vend + 200_000, bgm_vol, field="volume")
            cur = vend + 200_000
        # 末尾维持
        add_keyframe(draft, bgm_sid, cur, bgm_vol, field="volume")

    # 保存
    draft.save()
    print(f"\n✓ 完成。")
    print(f"  项目时长: {draft.duration_hms}")
    print(f"  V1: 主视频（全屏）")
    print(f"  V2: 画中画（30% 缩放，右下角）")
    print(f"  A1: 背景音乐（ducking 已应用）")
    print(f"  请在剪映中重新打开项目查看。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="双轨混剪示例")
    parser.add_argument("--project", required=True, help="剪映项目名")
    parser.add_argument("--main", required=True, help="主视频文件")
    parser.add_argument("--pip", required=True, help="画中画视频文件")
    parser.add_argument("--bgm", required=True, help="背景音乐文件")
    args = parser.parse_args()

    setup_multitrack(args.project, args.main, args.pip, args.bgm)
