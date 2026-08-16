from pathlib import Path

from avs.config import Config


ROOT = Path(__file__).resolve().parents[1]


def test_creator_os_v2_config_contract_loads():
    config = Config(ROOT)
    assert config.validate_all() == []
    assert config.project["project"]["name"] == "Creator OS"
    assert config.project["project"]["publish_success_state"] == "READY_TO_PUBLISH"
    assert config.public_lifecycle[-1] == "READY_TO_PUBLISH"


def test_creator_os_v2_formats_are_frozen():
    config = Config(ROOT)
    assert set(config.content_formats["format_router"]["allowed"]) == {
        "VIDEO",
        "CAROUSEL",
        "TEXT",
    }


def test_douyin_acquisition_degrades_honestly():
    config = Config(ROOT)
    douyin = config.reference_acquisition["reference_acquisition"]["sources"]["douyin_url"]
    assert douyin["failure_behavior"] == "degrade_honestly"
    assert douyin["bypass_login_or_access_controls"] is False


def test_video_timing_forbids_character_count_alignment():
    config = Config(ROOT)
    timing = config.voice["voice"]["video_timing"]
    assert timing["narration_master_is_clock"] is True
    assert timing["forbid_character_count_timing"] is True
