"""Professional edit planning and export QA tests."""
from pathlib import Path
import sys


SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def test_short_form_prompt_produces_director_plan():
    from cut.director import create_edit_plan

    assets = [
        {"path": "a.mp4", "duration_us": 8_000_000, "has_audio": True},
        {"path": "b.mp4", "duration_us": 12_000_000, "has_audio": True},
        {"path": "bgm.mp3", "duration_us": 60_000_000, "type": "audio"},
    ]
    plan = create_edit_plan("自动做一个60秒旅行vlog，适合抖音，节奏轻快", assets)

    assert plan["format"] == "short_form"
    assert plan["target_platform"] == "douyin"
    assert plan["target_duration_us"] == 60_000_000
    assert plan["style"]["pace"] == "fast"
    assert plan["qa_required"] is True
    action_names = [step["action"] for step in plan["steps"]]
    assert action_names[:2] == ["detect", "get_state"]
    assert "assemble_rough_cut" in action_names
    assert "add_subtitles" in action_names
    assert "sound_mix" in action_names
    assert "export" in action_names
    assert "quality_check" in action_names


def test_long_form_prompt_uses_story_structure():
    from cut.director import create_edit_plan

    plan = create_edit_plan("把素材剪成30分钟影视解说长视频，沉稳电影感", [])

    assert plan["format"] == "long_form"
    assert plan["target_duration_us"] == 1_800_000_000
    assert plan["style"]["pace"] == "steady"
    assert plan["story_structure"] == ["hook", "setup", "development", "turning_point", "payoff"]


def test_quality_report_flags_export_problems():
    from cut.quality import analyze_export

    ffprobe = {
        "format": {
            "duration": "58.0",
            "bit_rate": "700000",
        },
        "streams": [
            {"codec_type": "video", "width": 1920, "height": 1080, "r_frame_rate": "30/1"},
            {"codec_type": "audio", "sample_rate": "48000", "channels": 2},
        ],
    }
    report = analyze_export(
        "out.mp4",
        expected_duration_us=60_000_000,
        ffprobe_json=ffprobe,
        min_video_bitrate=1_000_000,
    )

    assert report["success"] is False
    assert report["duration_us"] == 58_000_000
    assert any("duration" in item["code"] for item in report["findings"])
    assert any("bitrate" in item["code"] for item in report["findings"])


def main():
    test_short_form_prompt_produces_director_plan()
    print("[1] Short-form director plan")
    test_long_form_prompt_uses_story_structure()
    print("[2] Long-form story structure")
    test_quality_report_flags_export_problems()
    print("[3] Export QA findings")
    print("\nOK Professional workflow tests passed")


if __name__ == "__main__":
    main()
