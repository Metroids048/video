"""测试专业剪辑能力：一键成片端到端。"""
import json
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

from test_e2e import make_empty_draft, make_fake_video
from cut.jianying.draft import Draft
from cut.jianying import materials, auto_edit, viral_templates
from cut.jianying.pro_color import generate_all_luts, COLOR_PRESETS
from cut.jianying.pro_text import HUAZI_PRESETS
from cut.jianying.pro_effects import PRO_TRANSITION_PRESETS


def test_lut_generation():
    with tempfile.TemporaryDirectory() as tmp:
        r = generate_all_luts(tmp, size=8)
        assert r["generated"] == len(COLOR_PRESETS)
        for f in r["files"]:
            assert Path(f).exists()
            assert Path(f).stat().st_size > 0
        assert Path(r["readme"]).exists()
    print(f"[1] LUT 生成: {r['generated']} 个 .cube 文件 ✓")


def test_template_apply():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        project_dir = tmp_p / "viral_test"
        make_empty_draft(project_dir)
        draft = Draft.open(project_dir=project_dir)

        mat_ids = []
        for i in range(7):
            v = tmp_p / f"v{i}.mp4"
            make_fake_video(str(v))
            mid = materials.import_video(draft, str(v), alias=f"clip_{i}")
            draft.find_material(mid)["duration"] = 8_000_000
            mat_ids.append(mid)

        bgm = tmp_p / "bgm.mp3"
        make_fake_video(str(bgm))
        bgm_mid = materials.import_audio(draft, str(bgm), alias="bgm")
        draft.find_material(bgm_mid)["duration"] = 60_000_000

        result = auto_edit.auto_edit(
            draft, mat_ids, bgm_material_id=bgm_mid,
            template="vlog",
            texts=["我的一天", "早晨", "工作", "高光", "晚上", "感悟", "再见"],
            auto_subtitle=False,
        )

        print(f"[2] 模板应用:")
        print(f"    template: {result['template']}")
        print(f"    total: {result['total_duration_hms']}")
        print(f"    steps: {len(result['steps'])}")
        print(f"    errors: {len(result['errors'])}")

        assert result["success"] or len(result["errors"]) <= 2
        draft.save()

        draft2 = Draft.open(project_dir=project_dir)
        assert len(draft2.video_tracks[0].segments) == 7
        assert len(draft2.text_tracks[0].segments) == 7
        assert len(draft2.audio_tracks) >= 1
        assert len(draft2.materials.get("effects", [])) >= 7
        print(f"    segments: V={len(draft2.video_tracks[0].segments)}, T={len(draft2.text_tracks[0].segments)}")


def test_imitate_viral():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        project_dir = tmp_p / "imitate_test"
        make_empty_draft(project_dir)
        draft = Draft.open(project_dir=project_dir)

        mat_ids = []
        for i in range(5):
            v = tmp_p / f"v{i}.mp4"
            make_fake_video(str(v))
            mid = materials.import_video(draft, str(v), alias=f"clip_{i}")
            draft.find_material(mid)["duration"] = 10_000_000
            mat_ids.append(mid)

        reference = {
            "template": "tutorial",
            "duration_us": 40_000_000,
            "color_preset": "teal_orange",
            "texts": ["AI剪辑太难？", "今天教你一键成片", "第一步：导入素材",
                     "第二步：选择模板", "第三步：自动卡点", "就这么简单", "关注学更多"],
            "auto_subtitle": False,
        }

        result = auto_edit.imitate_viral(draft, reference, mat_ids)
        print(f"[3] 模仿爆款:")
        print(f"    template: {result['template']}")
        print(f"    total: {result['total_duration_hms']}")
        assert result["success"] or len(result["errors"]) <= 2

        draft.save()
        draft2 = Draft.open(project_dir=project_dir)
        assert len(draft2.video_tracks[0].segments) == 7


def test_pro_effects():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        project_dir = tmp_p / "pro_fx_test"
        make_empty_draft(project_dir)
        draft = Draft.open(project_dir=project_dir)

        mids = []
        for i in range(2):
            v = tmp_p / f"v{i}.mp4"
            make_fake_video(str(v))
            mid = materials.import_video(draft, str(v))
            draft.find_material(mid)["duration"] = 5_000_000
            mids.append(mid)

        s1 = materials.add_video_segment(draft, mids[0], start_us=0, duration_us=5_000_000)
        s2 = materials.add_video_segment(draft, mids[1], start_us=5_000_000, duration_us=5_000_000)

        from cut.jianying.pro_effects import apply_pro_transition
        presets_tested = []
        for preset in ["smooth", "flash_white", "flash_black", "zoom_in", "zoom_out", "motion_blur"]:
            try:
                r = apply_pro_transition(draft, s1, s2, preset=preset)
                presets_tested.append(preset)
            except Exception as e:
                print(f"    {preset} 失败: {e}")

        print(f"[4] 专业转场: {len(presets_tested)}/{len(PRO_TRANSITION_PRESETS)} presets ✓")
        assert len(presets_tested) >= 4

        s1_raw = draft.get_segment_raw(s1)
        kfs = s1_raw.get("common_keyframes", [])
        assert len(kfs) > 0
        print(f"    s1 关键帧数: {len(kfs)}")


def main():
    print("=== 专业剪辑能力测试 ===\n")
    test_lut_generation()
    test_template_apply()
    test_imitate_viral()
    test_pro_effects()
    print("\n✅ 所有专业能力测试通过")


if __name__ == "__main__":
    main()
