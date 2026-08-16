from pathlib import Path

from avs.config import Config

ROOT = Path(__file__).resolve().parents[1]


def test_creator_os_v2_config_contract_loads():
    config = Config(ROOT)
    assert config.validate_all() == []
    project = config.project["project"]
    assert project["name"] == "Creator OS"
    assert str(project["version"]) == "2.3"
    assert project["publish_success_state"] == "READY_TO_PUBLISH"
    assert project["release_gate_fail_closed"] is True
    assert project["delivery_requires_current_video_release_review"] is True
    assert project["release_review_must_match_current_sha256"] is True
    assert project["release_review_must_match_current_source_sha256s"] is True
    assert project["release_review_requires_source_to_final_fidelity"] is True
    assert project["video_release_review_record"] == "work/qa/video-release-review.json"
    assert config.public_lifecycle[-1] == "READY_TO_PUBLISH"
    assert "video-review.yaml" in config.required_config_files


def test_creator_os_v2_formats_are_frozen():
    config = Config(ROOT)
    assert set(config.content_formats["format_router"]["allowed"]) == {"VIDEO", "CAROUSEL", "TEXT"}
    assert config.content_pillars["content_pillars"]["default_mode"] == "ORIGINAL"


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


def test_video_review_contract_is_loaded_and_blocks_known_bad_delivery():
    config = Config(ROOT)
    review = config.video_review["video_review"]

    assert "original source artifacts actually used" in review["source_of_truth"]
    assert review["required_review_views"]["source_to_final_fidelity"]["required"] is True
    assert review["required_review_views"]["full_frame_integrity"]["required"] is True
    assert review["required_review_views"]["spatial_continuity"]["required"] is True
    assert review["required_review_views"]["temporal_continuity"]["required"] is True
    assert review["required_review_views"]["continuous_playback_1x"]["required"] is True
    assert review["required_review_views"]["first_second_review"]["required"] is True
    assert review["required_review_views"]["first_10s_dense_review"]["required"] is True
    assert review["hard_fail_conditions"]["unauthorized_destructive_crop"]["fail"] is True
    assert review["hard_fail_conditions"]["source_frame_context_lost"]["fail"] is True
    assert review["hard_fail_conditions"]["spatial_continuity_broken"]["fail"] is True
    assert review["hard_fail_conditions"]["temporal_continuity_broken"]["fail"] is True
    assert review["hard_fail_conditions"]["first_frame_partial_or_mid_action"]["fail"] is True
    assert review["hard_fail_conditions"]["slideshow_feel"]["fail"] is True
    assert review["hard_fail_conditions"]["static_screenshot_pan_zoom_dominant"]["fail"] is True
    assert review["hard_fail_conditions"]["key_evidence_requires_pause"]["fail"] is True
    assert review["hard_fail_conditions"]["rapid_dark_light_switching"]["fail"] is True
    assert review["repair_loop"]["mandatory_when_failed"] is True
    assert review["repair_loop"]["full_rewatch_after_every_repair"] is True
    assert review["delivery_gate"]["only_status_allowed"] == "READY_TO_PUBLISH"
    assert review["delivery_gate"]["validated_record_required"] is True
    assert review["delivery_gate"]["current_sha256_match_required"] is True
    assert review["delivery_gate"]["current_source_sha256s_match_required"] is True
    assert review["delivery_gate"]["source_fidelity_pass_required"] is True


def test_quality_config_requires_machine_validated_release_review():
    config = Config(ROOT)
    quality = config.quality["quality"]

    assert quality["publishable"]["require_video_release_review_record"] is True
    assert quality["publishable"]["require_release_review_current_sha256"] is True
    assert quality["publishable"]["require_source_to_final_fidelity_review"] is True
    assert quality["publishable"]["require_source_artifact_hashes"] is True
    assert quality["publishable"]["require_no_unauthorized_destructive_crop"] is True
    assert quality["release_gate"]["fail_closed"] is True
    assert quality["release_gate"]["metadata_only_review"] == "BLOCK"
    assert quality["release_gate"]["contact_sheet_only_review"] == "BLOCK"
    assert quality["release_gate"]["missing_source_fidelity_review"] == "BLOCK"
    assert quality["release_gate"]["stale_source_hash"] == "BLOCK"
    assert quality["release_gate"]["any_hard_fail"] == "REPAIR"
    assert quality["repair"]["require_new_release_review_after_media_change"] is True


def test_workflow_places_source_fidelity_and_release_review_before_approval_and_delivery():
    config = Config(ROOT)
    workflow = config.workflow["workflow"]
    stages = workflow["stages"]

    source_inventory = stages.index("source-inventory")
    source_fidelity = stages.index("source-to-final-fidelity-review")
    continuous = stages.index("continuous-video-review")
    validate = stages.index("validate-video-release-review")
    approval = stages.index("approval")
    delivery = stages.index("delivery")
    assert source_inventory < source_fidelity < continuous < validate < approval < delivery
    assert workflow["video_release_gate"]["fail_closed"] is True
    assert workflow["video_release_gate"]["requires_source_inventory"] is True
    assert workflow["video_release_gate"]["requires_source_to_final_fidelity_review"] is True
    assert workflow["video_release_gate"]["requires_current_source_sha256s"] is True
    assert workflow["video_release_gate"]["approval_must_happen_after_gate"] is True
    assert workflow["video_release_gate"]["delivery_must_reverify_gate"] is True
