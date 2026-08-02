"""端到端测试：模拟完整的剪辑工作流。

构造场景：
1. 创建空项目
2. 导入 3 个视频素材 + 1 个音频素材
3. 把视频按顺序排到 V1
4. 把音频放到 A1
5. 在第 1 个视频中间切一刀
6. 给每两个相邻视频之间加转场
7. 加几个字幕
8. 给第 1 个视频加暗角特效
9. 给音频做 ducking（模拟语音段）
10. 重读 draft 验证所有修改
11. 测试 state 反向读取
12. 测试 context 统一接口

不依赖剪映/Premiere 实际运行，纯 Python 测试 draft 操控逻辑。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from cut.jianying.draft import Draft, _new_id
from cut.jianying import materials, segments, text, effects, audio, state
from cut.jianying import export as export_mod
from cut import context, platform as P


def make_empty_draft(project_dir: Path):
    """创建空 draft 项目。"""
    content = {
        "version": "5.9.0",
        "draft_version": "5.9.0",
        "duration": 0,
        "canvas_config": {"width": 1920, "height": 1080, "ratio": "original"},
        "id": "e2e-test",
        "create_time": 1700000000,
        "fps": 30,
        "materials": {
            "videos": [], "audios": [], "images": [],
            "stickers": [], "texts": [], "effects": [], "audio_effects": [],
            "material_animations": [], "video_effects": [],
        },
        "tracks": [],
    }
    project_dir.mkdir(parents=True, exist_ok=True)
    with open(project_dir / "draft_content.json", "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False)


def make_fake_video(path: str, duration_us: int = 5_000_000):
    """创建假的视频文件（仅占位，内容不重要，materials.import_video 用 ffprobe 探测会失败但不阻断）。"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(b"\x00" * 100)


def test_e2e_workflow():
    """端到端工作流测试。"""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        project_dir = tmp / "e2e_project"
        make_empty_draft(project_dir)

        # 准备假素材文件
        v1 = tmp / "media" / "v1.mp4"
        v2 = tmp / "media" / "v2.mp4"
        v3 = tmp / "media" / "v3.mp4"
        a1 = tmp / "media" / "bgm.mp3"
        for f in [v1, v2, v3, a1]:
            make_fake_video(str(f))

        # === 1. 打开项目 ===
        draft = Draft.open(project_dir=project_dir)
        print(f"[1] 打开项目: {draft.name}, 时长 {draft.duration_hms}")
        assert draft.duration == 0
        assert len(draft.all_tracks()) == 0

        # === 2. 导入素材 ===
        # 由于 ffprobe 可能未装，duration 会为 0，我们直接构造 material 绕过探测
        # 这里测试 import_video 的正常路径
        m1 = materials.import_video(draft, str(v1), alias="视频1")
        m2 = materials.import_video(draft, str(v2), alias="视频2")
        m3 = materials.import_video(draft, str(v3), alias="视频3")
        ma = materials.import_audio(draft, str(a1), alias="背景音乐")
        print(f"[2] 导入素材: 3 video + 1 audio")
        assert len(draft.list_materials(mtype="video")) == 3
        assert len(draft.list_materials(mtype="audio")) == 1

        # 由于 ffprobe 失败，duration 是 0。手动设置素材 duration 让后续逻辑可走
        for mat_id in [m1, m2, m3]:
            mat = draft.find_material(mat_id)
            mat["duration"] = 5_000_000
            mat["width"] = 1920
            mat["height"] = 1080
        draft.find_material(ma)["duration"] = 15_000_000

        # === 3. 视频按顺序排到 V1 ===
        # 因为 draft 没有 video track，add_video_segment 会自动创建
        s1 = materials.add_video_segment(draft, m1, start_us=0, duration_us=5_000_000)
        s2 = materials.add_video_segment(draft, m2, start_us=5_000_000, duration_us=5_000_000)
        s3 = materials.add_video_segment(draft, m3, start_us=10_000_000, duration_us=5_000_000)
        print(f"[3] 视频排到 V1: 3 segments, 项目时长 {draft.duration_hms}")
        assert draft.duration == 15_000_000
        assert len(draft.video_tracks) == 1
        assert len(draft.video_tracks[0].segments) == 3

        # === 4. 音频放到 A1 ===
        sa = materials.add_audio_segment(draft, ma, start_us=0, duration_us=15_000_000, volume=0.4)
        print(f"[4] 音频放 A1: segment_id={sa[:8]}")
        assert len(draft.audio_tracks) == 1
        assert draft.audio_tracks[0].segments[0].volume == 0.4

        # === 5. 在第 1 个视频中间切一刀 ===
        seg1 = draft.video_tracks[0].segments[0]
        left, right = segments.split_segment(draft, seg1, at_us=2_500_000)
        print(f"[5] 切分 V1[0]: left={left[:8]} right={right[:8]}")
        assert len(draft.video_tracks[0].segments) == 4  # 3 -> 4
        # 验证切分后顺序与时间
        segs = draft.video_tracks[0].segments
        assert segs[0].start_us == 0 and segs[0].end_us == 2_500_000
        assert segs[1].start_us == 2_500_000 and segs[1].end_us == 5_000_000
        assert segs[2].start_us == 5_000_000 and segs[2].end_us == 10_000_000

        # === 6. 相邻视频间加转场 ===
        # track_id 是 video_tracks[0].id
        vt_id = draft.video_tracks[0].id
        t1 = effects.add_transition_simple(draft, vt_id, 0, preset="fade", duration_us=500_000)
        t2 = effects.add_transition_simple(draft, vt_id, 1, preset="slide_left", duration_us=300_000)
        t3 = effects.add_transition_simple(draft, vt_id, 2, preset="zoom_in", duration_us=400_000)
        print(f"[6] 加 3 个转场")
        # 验证
        track_raw = next(t for t in draft.tracks_raw if t["id"] == vt_id)
        assert len(track_raw.get("transitions", [])) == 3

        # === 7. 加字幕 ===
        tx1 = text.add_subtitle(draft, "欢迎观看", start_us=0, duration_us=2_500_000)
        tx2 = text.add_subtitle(draft, "今天我们来聊聊", start_us=2_500_000, duration_us=2_500_000)
        tx3 = text.add_title(draft, "精彩内容", start_us=5_000_000, duration_us=2_000_000)
        print(f"[7] 加 3 个字幕")
        assert len(draft.text_tracks) == 1
        assert len(draft.text_tracks[0].segments) == 3

        # === 8. 给第 1 个视频加暗角特效 ===
        first_seg_id = draft.video_tracks[0].segments[0].id
        fx_id = effects.add_video_effect(draft, first_seg_id, preset="vignette", intensity=0.8)
        print(f"[8] 加暗角特效: effect_segment_id={fx_id[:8]}")
        assert len(draft.effect_tracks) == 1
        assert len(draft.effect_tracks[0].segments) == 1

        # === 9. 给音频做 ducking ===
        # 模拟 5-10s 有语音
        audio.apply_ducking(
            draft,
            voice_segment_ids=[tx2],  # 用字幕段当作"语音段"的代理
            bgm_segment_id=sa,
            duck_level=0.3,
            fade_us=200_000,
        )
        print(f"[9] ducking 已应用")
        bgm_seg = draft.get_segment_raw(sa)
        assert len(bgm_seg.get("common_keyframes", [])) > 0

        # === 10. 保存并重读 ===
        draft.save()
        draft2 = Draft.open(project_dir=project_dir)
        print(f"[10] 保存重读: 时长 {draft2.duration_hms}")
        assert draft2.duration == 15_000_000
        assert len(draft2.video_tracks[0].segments) == 4
        assert len(draft2.audio_tracks[0].segments) == 1
        assert len(draft2.text_tracks[0].segments) == 3
        assert len(draft2.effect_tracks[0].segments) == 1
        track_raw2 = next(t for t in draft2.tracks_raw if t["id"] == vt_id)
        assert len(track_raw2.get("transitions", [])) == 3

        # === 11. 验证 JSON 合法性 ===
        with open(project_dir / "draft_content.json", "r", encoding="utf-8") as f:
            content = json.load(f)
        assert content["duration"] == 15_000_000
        # 验证 ID 唯一性
        all_ids = []
        for t in content["tracks"]:
            all_ids.append(t["id"])
            for s in t.get("segments", []):
                all_ids.append(s["id"])
            for tr in t.get("transitions", []):
                all_ids.append(tr["id"])
        for k in ("videos", "audios", "texts", "effects"):
            for m in content["materials"].get(k, []):
                all_ids.append(m["id"])
        assert len(all_ids) == len(set(all_ids)), f"ID 重复: {[i for i in all_ids if all_ids.count(i) > 1]}"
        print(f"[11] JSON 合法，所有 {len(all_ids)} 个 ID 唯一")

        # === 12. 测试 state 反向读取 ===
        st = state.get_state(project_dir=str(project_dir))
        assert st["backend"] == "jianying"
        assert st["duration_us"] == 15_000_000
        assert st["project_name"] == "e2e_project"
        # tracks 概要
        track_types = {t["type"] for t in st["tracks"]}
        assert track_types == {"video", "audio", "text", "effect"}
        print(f"[12] state 读取: tracks={[(t['type'], t['segments_count']) for t in st['tracks']]}")

        # === 13. 测试 timeline 完整读取 ===
        tl = state.get_timeline(project_dir=str(project_dir))
        assert tl["duration_us"] == 15_000_000
        v_track = next(t for t in tl["tracks"] if t["type"] == "video")
        assert len(v_track["segments"]) == 4
        # 验证每个 segment 都有 material_path
        for seg in v_track["segments"]:
            assert seg["material_path"]  # 不为空
            assert seg["start_hms"]
        print(f"[13] timeline 读取: {len(tl['tracks'])} tracks, V1 有 {len(v_track['segments'])} segments")

        # === 14. 测试 find_gaps ===
        # 故意删一个 segment 中间留空隙
        # 实际上目前连续，应该没有 gap
        gaps = state.find_gaps(tl)
        video_gaps = [g for g in gaps if g["track_type"] == "video"]
        print(f"[14] video gaps: {len(video_gaps)} (应为 0)")
        # 末尾可能有 gap（duration 15s，最后 segment 到 15s 结束，应该没 gap）
        assert len(video_gaps) == 0

        # === 15. 测试 get_segments_at ===
        at_3s = state.get_segments_at(tl, 3_000_000)
        # 3s 在 video 段 2.5-5s 内
        types_at_3s = [s["track_type"] for s in at_3s]
        assert "video" in types_at_3s
        assert "audio" in types_at_3s
        # 3s 也在字幕 tx2 (2.5-5s) 内
        assert "text" in types_at_3s
        print(f"[15] 3s 处的 segments: {types_at_3s}")

        # === 16. 测试 context 统一接口 ===
        env = context.detect_environment()
        assert env["platform"] in ("windows", "darwin", "linux")
        print(f"[16] context.detect_environment: platform={env['platform']}")

        # === 17. 测试 list_materials 接口 ===
        ms = context.list_materials(backend="jianying", project_dir=str(project_dir))
        # 3 video + 1 audio + 3 text + 1 effect (vignette) = 8
        assert len(ms) == 8, f"期望 8 个素材，实际 {len(ms)}"
        type_counts = {}
        for m in ms:
            type_counts[m["type"]] = type_counts.get(m["type"], 0) + 1
        assert type_counts.get("video", 0) == 3
        assert type_counts.get("audio", 0) == 1
        assert type_counts.get("text", 0) == 3
        assert type_counts.get("effect", 0) == 1
        print(f"[17] context.list_materials: {type_counts}")

        # === 18. 测试 remove_segment (ripple) ===
        # 删除 V1 第 4 个（最后一段，10-15s），ripple 模式
        last_seg = draft2.video_tracks[0].segments[-1]
        segments.remove_segment(draft2, last_seg.id, ripple=True)
        print(f"[18] ripple delete 最后一段: V1 现有 {len(draft2.video_tracks[0].segments)} segments")
        assert len(draft2.video_tracks[0].segments) == 3
        draft2.save()

        # === 19. 测试 trim ===
        draft3 = Draft.open(project_dir=project_dir)
        seg0 = draft3.video_tracks[0].segments[0]
        # 把第 0 段从 0-2.5s 改成 0.5-2s
        segments.trim_segment(draft3, seg0, new_start_us=500_000, new_end_us=2_000_000)
        seg0_after = draft3.video_tracks[0].segments[0]
        assert seg0_after.start_us == 500_000
        assert seg0_after.end_us == 2_000_000
        print(f"[19] trim: V1[0] 现为 [{seg0_after.start_us}-{seg0_after.end_us}]")

        # === 20. 测试 update_text_content ===
        text.update_text_content(draft3, tx1, "修改后的字幕")
        mat = draft3.find_material(draft3.video_tracks[0].segments[0].material_id)
        # tx1 是 text segment
        tx1_seg = draft3.get_segment_raw(tx1)
        tx1_mat = draft3.find_material(tx1_seg["material_id"])
        assert tx1_mat["text"] == "修改后的字幕"
        print(f"[20] 修改字幕内容: '{tx1_mat['text']}'")

        print("\n✅ 所有端到端测试通过")


if __name__ == "__main__":
    test_e2e_workflow()
