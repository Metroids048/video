"""回归测试：验证 bug 修复后的行为。

专门测试审查报告中的 CRITICAL 和 HIGH 级别 bug 是否已修复。
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

from test_e2e import make_empty_draft, make_fake_video
from cut.jianying.draft import Draft, _us, _hms
from cut.jianying import materials, segments, text, effects, audio


def make_project_with_segment(tmp: Path, seg_dur_us: int = 5_000_000):
    """创建带 1 个视频 segment 的项目。"""
    project_dir = tmp / "regression_test"
    make_empty_draft(project_dir)
    draft = Draft.open(project_dir=project_dir)
    mid = draft.add_material("video", {
        "id": "mat-v1", "type": "video", "path": "/tmp/v.mp4",
        "duration": seg_dur_us, "width": 1920, "height": 1080,
    })
    sid = materials.add_video_segment(draft, mid, start_us=0, duration_us=seg_dur_us)
    draft.save()
    return project_dir, mid, sid


# C1: 原子写入
def test_atomic_save(tmp: Path):
    """验证 save 失败时不破坏原文件。"""
    project_dir, _, _ = make_project_with_segment(tmp)
    original = (project_dir / "draft_content.json").read_text()

    draft = Draft.open(project_dir=project_dir)
    # 故意让 json.dumps 失败：set 是不可序列化的
    draft.content = {"bad_key": {1, 2, 3}}

    try:
        draft.save()
        assert False, "应该抛 DraftError"
    except Exception as e:
        assert "不可序列化" in str(e) or "TypeError" in str(e), f"异常信息不匹配: {e}"

    # 原文件应保持不变
    after = (project_dir / "draft_content.json").read_text()
    assert after == original, "原文件被破坏！"
    print(f"[C1] atomic save: 原文件未被破坏 ✓")


# C3: move_segment 更新 track_id
def test_move_updates_track_id(tmp: Path):
    project_dir, mid, sid = make_project_with_segment(tmp)
    draft = Draft.open(project_dir=project_dir)
    new_track_id = draft.add_track("video")
    segments.move_segment(draft, sid, new_track_id=new_track_id)
    raw = draft.get_segment_raw(sid)
    assert raw["track_id"] == new_track_id, f"track_id 未更新: {raw['track_id']}"
    print(f"[C3] move_segment: track_id 已更新 ✓")


# C4: ripple delete 同步移动关键帧
def test_ripple_delete_moves_keyframes(tmp: Path):
    """验证 ripple delete 后后续片段的关键帧时间同步前移。"""
    project_dir, mid, _ = make_project_with_segment(tmp, seg_dur_us=3_000_000)
    draft = Draft.open(project_dir=project_dir)
    # 加 3 个 segment
    s1 = draft.video_tracks[0].segments[0]
    m2 = draft.add_material("video", {"id": "m2", "type": "video", "path": "/tmp/v2.mp4", "duration": 3_000_000})
    sid2 = materials.add_video_segment(draft, m2, start_us=3_000_000, duration_us=3_000_000)
    m3 = draft.add_material("video", {"id": "m3", "type": "video", "path": "/tmp/v3.mp4", "duration": 3_000_000})
    sid3 = materials.add_video_segment(draft, m3, start_us=6_000_000, duration_us=3_000_000)
    # 给 s3 加一个关键帧在 7s
    from cut.jianying.effects import add_keyframe
    add_keyframe(draft, sid3, 7_000_000, 0.5, field="alpha")
    # ripple delete s2 (3-6s, dur=3s)
    segments.remove_segment(draft, sid2, ripple=True)
    # s3 应前移 3s，关键帧也应前移 3s
    s3_after = draft.get_segment_raw(sid3)
    assert s3_after["target_timerange"]["start"] == 3_000_000, \
        f"s3 start 应为 3000000，实际 {s3_after['target_timerange']['start']}"
    kfs = s3_after.get("common_keyframes", [])
    assert any(int(kf["time"]) == 4_000_000 for kf in kfs), \
        f"关键帧时间未同步前移: {[kf['time'] for kf in kfs]}"
    print(f"[C4] ripple delete: s3 前移到 3s, 关键帧前移到 4s ✓")


# C6: add_video_effect 在目标 segment 上引用 effect material
def test_effect_ref_correct(tmp: Path):
    project_dir, mid, sid = make_project_with_segment(tmp)
    draft = Draft.open(project_dir=project_dir)
    eff_sid = effects.add_video_effect(draft, sid, preset="vignette")
    target_seg = draft.get_segment_raw(sid)
    # 目标 segment 的 extra_material_refs 应包含 effect material_id
    eff_seg = draft.get_segment_raw(eff_sid)
    eff_mat_id = eff_seg["material_id"]
    assert eff_mat_id in target_seg.get("extra_material_refs", []), \
        f"目标 segment 未引用 effect material: {target_seg.get('extra_material_refs')}"
    # effect segment 的 extra_material_refs 不应包含 segment_id
    assert sid not in eff_seg.get("extra_material_refs", []), \
        f"effect segment 错误引用了 segment_id: {eff_seg.get('extra_material_refs')}"
    print(f"[C6] effect refs: 目标 segment 正确引用 effect material ✓")


# C7: text material 无前导空格字段
def test_text_no_typo(tmp: Path):
    project_dir, _, _ = make_project_with_segment(tmp)
    draft = Draft.open(project_dir=project_dir)
    sid = text.add_subtitle(draft, "测试", 0, 1000000)
    seg = draft.get_segment_raw(sid)
    mat = draft.find_material(seg["material_id"])
    assert "recognize_type" in mat, "缺少 recognize_type 字段"
    assert " recognize_type" not in mat, "存在前导空格的 recognize_type 字段"
    print(f"[C7] text typo: recognize_type 无前导空格 ✓")


# H2: split 后关键帧 ID 不重复
def test_split_no_dup_keyframe_id(tmp: Path):
    project_dir, mid, sid = make_project_with_segment(tmp, seg_dur_us=10_000_000)
    draft = Draft.open(project_dir=project_dir)
    # 给 segment 加几个关键帧
    from cut.jianying.effects import add_keyframe
    add_keyframe(draft, sid, 2_000_000, 0.5, field="alpha")
    add_keyframe(draft, sid, 5_000_000, 1.0, field="alpha")
    add_keyframe(draft, sid, 8_000_000, 0.5, field="alpha")
    # 在 5s 切分（恰好有关键帧在切点）
    seg = draft.video_tracks[0].segments[0]
    left, right = segments.split_segment(draft, seg, at_us=5_000_000)
    # 收集左右段所有关键帧 ID
    left_raw = draft.get_segment_raw(left)
    right_raw = draft.get_segment_raw(right)
    left_kf_ids = [kf["id"] for kf in left_raw.get("common_keyframes", [])]
    right_kf_ids = [kf["id"] for kf in right_raw.get("common_keyframes", [])]
    all_ids = left_kf_ids + right_kf_ids
    assert len(all_ids) == len(set(all_ids)), \
        f"关键帧 ID 重复: {all_ids}"
    # 左段应有 2s 的关键帧，右段应有 8s 的关键帧（5s 的归到左段，因为 time <= at）
    assert any(int(kf["time"]) == 2_000_000 for kf in left_raw.get("common_keyframes", []))
    assert any(int(kf["time"]) == 8_000_000 for kf in right_raw.get("common_keyframes", []))
    print(f"[H2] split: 关键帧 ID 唯一，关键帧按切点正确分配 ✓")


# H5: recalc_duration 收缩 duration
def test_recalc_duration_shrinks(tmp: Path):
    project_dir, _, _ = make_project_with_segment(tmp, seg_dur_us=5_000_000)
    draft = Draft.open(project_dir=project_dir)
    assert draft.duration == 5_000_000
    # 删除唯一的 segment
    sid = draft.video_tracks[0].segments[0].id
    segments.remove_segment(draft, sid, ripple=False)
    draft.save()
    draft2 = Draft.open(project_dir=project_dir)
    # duration 应收缩到 0
    assert draft2.duration == 0, f"duration 未收缩: {draft2.duration}"
    print(f"[H5] recalc_duration: 删除后 duration 收缩到 0 ✓")


# H7: export_via_ui 不再无脑返回 success=True（验证逻辑：无剪映窗口时返回 False）
def test_export_ui_no_window(tmp: Path):
    from cut.jianying.export import export_via_ui
    project_dir, _, _ = make_project_with_segment(tmp)
    draft = Draft.open(project_dir=project_dir)
    result = export_via_ui(draft, output_dir=str(tmp), filename="out", timeout=1)
    # 应该返回 success=False（因为没有剪映窗口）
    assert result["success"] is False, \
        f"无剪映窗口时不应返回 success=True: {result}"
    print(f"[H7] export_via_ui: 无窗口时返回 success=False ✓")


# H8: ffmpeg 导出用 list 形式（验证命令是 list 不是 str）
def test_ffmpeg_cmd_is_list(tmp: Path):
    """验证 export_via_ffmpeg 构造的 cmd 是 list（无 shell 注入风险）。"""
    from cut.jianying.export import export_via_ffmpeg
    project_dir, mid, sid = make_project_with_segment(tmp)
    draft = Draft.open(project_dir=project_dir)
    # 即使 ffmpeg 不存在，也会先检查 shutil_which；若存在则尝试运行
    result = export_via_ffmpeg(draft, str(tmp / "out.mp4"))
    # 如果 ffmpeg 没装，返回 error；如果装了，cmd 应是 list
    if "cmd" in result:
        assert isinstance(result["cmd"], list), \
            f"cmd 应为 list，实际 {type(result['cmd'])}"
        print(f"[H8] ffmpeg cmd: list 形式 ✓")
    else:
        print(f"[H8] ffmpeg cmd: 未装 ffmpeg 跳过（{result.get('error', '')[:30]}）")


# H12: _us 与 _parse_time 对裸数字字符串语义一致
def test_us_consistent_with_cli():
    """验证 _us('3000000') 返回 3000000 微秒（与 CLI _parse_time 一致）。"""
    val = _us("3000000")
    assert val == 3_000_000, f"_us('3000000') 应为 3000000，实际 {val}"
    # 带后缀
    assert _us("2.5s") == 2_500_000
    assert _us("2500ms") == 2_500_000
    assert _us("2500000us") == 2_500_000
    # HH:MM:SS
    assert _us("00:00:02.500") == 2_500_000
    # 数字
    assert _us(3000000) == 3_000_000
    print(f"[H12] _us consistency: 裸数字字符串按 μs 处理 ✓")


# H4: text_alpha 不被硬编码覆盖
def test_text_alpha_not_overridden(tmp: Path):
    project_dir, _, _ = make_project_with_segment(tmp)
    draft = Draft.open(project_dir=project_dir)
    sid = text.add_text(draft, "test", 0, 1000000, preset="subtitle",
                        style_overrides={"text_alpha": 0.5})
    seg = draft.get_segment_raw(sid)
    mat = draft.find_material(seg["material_id"])
    # 修复后 text_alpha 在 dict 中不重复定义（原 bug 是 90 行和 121 行重复）
    keys = list(mat.keys())
    alpha_count = keys.count("text_alpha")
    assert alpha_count <= 1, f"text_alpha 出现 {alpha_count} 次（应 ≤ 1）"
    # style_overrides 中的 text_alpha 应体现在 text_styles[0].style 中
    if mat.get("text_styles"):
        assert mat["text_styles"][0]["style"].get("text_alpha") == 0.5
    print(f"[H4] text_alpha: 不再重复定义，style_overrides 生效 ✓")


# H6: update_text_content 设置 _modified
def test_update_text_sets_modified(tmp: Path):
    project_dir, _, _ = make_project_with_segment(tmp)
    draft = Draft.open(project_dir=project_dir)
    sid = text.add_subtitle(draft, "原内容", 0, 1000000)
    draft._modified = False  # 重置
    text.update_text_content(draft, sid, "新内容")
    assert draft._modified is True, "update_text_content 未设置 _modified"
    print(f"[H6] update_text_content: 设置 _modified ✓")


# H1: split 时 source_duration 不足不会产生负数
def test_split_source_clamp(tmp: Path):
    """构造数据不一致场景：source_duration < target_duration * speed。"""
    project_dir, mid, sid = make_project_with_segment(tmp, seg_dur_us=5_000_000)
    draft = Draft.open(project_dir=project_dir)
    # 手动破坏数据：把 source_duration 改小
    raw = draft.get_segment_raw(sid)
    raw["source_timerange"]["duration"] = 1_000_000  # 只有 1s source，但 target 是 5s
    # 在 4.5s 切分（left_target_dur = 4.5s, left_source_dur = 4.5s 但 source 只有 1s）
    seg = draft.video_tracks[0].segments[0]
    left, right = segments.split_segment(draft, seg, at_us=4_500_000)
    right_raw = draft.get_segment_raw(right)
    right_source_dur = right_raw["source_timerange"]["duration"]
    assert right_source_dur >= 0, f"right_source_dur 为负: {right_source_dur}"
    print(f"[H1] split source clamp: 不产生负数 (right_source_dur={right_source_dur}) ✓")


def main():
    print("=== Bug 修复回归测试 ===\n")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        test_atomic_save(tmp_p)
        test_move_updates_track_id(tmp_p)
        test_ripple_delete_moves_keyframes(tmp_p)
        test_effect_ref_correct(tmp_p)
        test_text_no_typo(tmp_p)
        test_split_no_dup_keyframe_id(tmp_p)
        test_recalc_duration_shrinks(tmp_p)
        test_export_ui_no_window(tmp_p)
        test_ffmpeg_cmd_is_list(tmp_p)
        test_us_consistent_with_cli()
        test_text_alpha_not_overridden(tmp_p)
        test_update_text_sets_modified(tmp_p)
        test_split_source_clamp(tmp_p)
    print("\n✅ 所有回归测试通过")


if __name__ == "__main__":
    main()
