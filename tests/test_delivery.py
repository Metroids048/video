"""Editable delivery package tests."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from avs.delivery.manifest import validate_manifest
from avs.delivery.package import run_delivery
from avs.models.episode import EpisodeModel


def _model(mode: str = "ORIGINAL", *, qa_passed: bool = True, publishable: bool = False) -> EpisodeModel:
    model = EpisodeModel.create("EP-DELIVERY-TEST", mode=mode, platforms=["douyin"])
    if publishable:
        model._data["publishable"] = True
    if not qa_passed:
        return model
    for status in ("INGESTED", "CONTENT_READY", "ASSETS_READY", "TIMELINE_READY", "ROUGH_CUT_READY", "QA_PASSED"):
        model.transition(status)
    return model


def _episode(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    episode = project / "episodes" / "active" / "EP-DELIVERY-TEST"
    (project / "schemas").mkdir(parents=True)

    # Copy delivery manifest schema
    schema = Path(__file__).parents[1] / "schemas" / "delivery-manifest.schema.json"
    shutil.copy2(schema, project / "schemas" / schema.name)

    # Copy visual-approval schema for approval validation
    approval_schema = Path(__file__).parents[1] / "schemas" / "visual-approval.schema.json"
    shutil.copy2(approval_schema, project / "schemas" / approval_schema.name)

    for relative in ("renders", "work/content", "work/prepared", "delivery/motion-graphics"):
        (episode / relative).mkdir(parents=True, exist_ok=True)
    (episode / "renders" / "preview-clean.mp4").write_bytes(b"clean")
    (episode / "renders" / "preview-with-captions.mp4").write_bytes(b"captions")
    (episode / "renders" / "preview-with-motion.mp4").write_bytes(b"motion")
    (episode / "work" / "captions.srt").write_text("1\n", encoding="utf-8")
    (episode / "work" / "timeline.csv").write_text("clip_id\n", encoding="utf-8")
    (episode / "work" / "prepared" / "used.mp4").write_bytes(b"asset")
    timeline = {
        "tracks": [{"kind": "video", "clips": [{"asset_ref": "work/prepared/used.mp4", "clip_id": "v1", "start": 0.0, "duration": 1.0}]}],
    }
    (episode / "work" / "timeline.json").write_text(json.dumps(timeline), encoding="utf-8")
    (episode / "work" / "content" / "script.json").write_text("{}", encoding="utf-8")
    (episode / "delivery" / "motion-graphics" / "hook.mp4").write_bytes(b"hook")
    (episode / "delivery" / "qa-report.json").write_text(json.dumps({
        "passed": True,
        "technical_passed": True,
        "publishability_passed": True,
        "human_approved": True,
        "blocking_reasons": [],
        "input_fingerprint": "test-fingerprint",
        "checks": [],
        "generated_at": "2025-01-01T00:00:00Z"
    }), encoding="utf-8")
    (episode / "delivery" / "qa-report.md").write_text("qa", encoding="utf-8")
    (episode / "delivery" / "visual-review.md").write_text("visual", encoding="utf-8")
    (episode / "delivery" / "qa-contact-sheet.jpg").write_bytes(b"jpg")

    # Add visual-approval.json for publishable episodes
    # Must compute hash from actual video file
    import hashlib
    final_video = episode / "renders" / "preview-with-motion.mp4"
    if not final_video.is_file():
        final_video = episode / "renders" / "preview-with-captions.mp4"
    if not final_video.is_file():
        final_video = episode / "renders" / "preview-clean.mp4"

    video_hash = hashlib.sha256(final_video.read_bytes()).hexdigest()
    video_relative = final_video.relative_to(episode).as_posix()

    approval = {
        "episode_id": "EP-DELIVERY-TEST",
        "approved": True,
        "reviewer": "Test Reviewer",
        "video_path": video_relative,
        "video_sha256": video_hash,
        "reviewed_at": "2025-01-01T00:00:00Z",
        "checklist": {
            "hook_clear_within_3s": True,
            "captions_readable": True,
            "composition_acceptable": True,
            "audio_acceptable": True,
            "no_placeholders": True,
            "facts_and_rights_checked": True
        },
        "notes": None
    }
    (episode / "delivery" / "visual-approval.json").write_text(json.dumps(approval), encoding="utf-8")

    return episode


def test_delivery_requires_qa_passed_status(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="QA_PASSED"):
        run_delivery(_episode(tmp_path), _model(qa_passed=False))


def test_delivery_copies_outputs_and_assets_into_delivery(tmp_path: Path) -> None:
    episode = _episode(tmp_path)
    manifest = run_delivery(episode, _model())

    assert (episode / "delivery" / "preview-clean.mp4").read_bytes() == b"clean"
    assert (episode / "delivery" / "timeline" / "timeline.json").is_file()
    assert (episode / "delivery" / "assets-used" / "used.mp4").read_bytes() == b"asset"
    assert all(item["path"].startswith("delivery/") for item in manifest["files"])
    assert all(not Path(item["path"]).is_absolute() for item in manifest["files"])
    validate_manifest(episode, manifest)


def test_delivery_preserves_content_and_reference_traceability(tmp_path: Path) -> None:
    episode = _episode(tmp_path)
    (episode / "work" / "content" / "brief.md").write_text("brief", encoding="utf-8")
    (episode / "work" / "content" / "missing-assets.md").write_text("gaps", encoding="utf-8")
    reference = episode / "work" / "reference" / "reference-recipe.json"
    reference.parent.mkdir(parents=True)
    reference.write_text("{}", encoding="utf-8")

    run_delivery(episode, _model())

    assert (episode / "delivery" / "content" / "brief.md").read_text(encoding="utf-8") == "brief"
    assert (episode / "delivery" / "content" / "missing-assets.md").read_text(encoding="utf-8") == "gaps"
    assert (episode / "delivery" / "reference" / "reference-recipe.json").read_text(encoding="utf-8") == "{}"


def test_delivery_refuses_changed_target_without_force(tmp_path: Path) -> None:
    episode = _episode(tmp_path)
    (episode / "delivery" / "preview-clean.mp4").write_bytes(b"different")
    with pytest.raises(FileExistsError, match="--force"):
        run_delivery(episode, _model())


def test_reference_clone_has_no_publish_copy(tmp_path: Path) -> None:
    episode = _episode(tmp_path)
    manifest = run_delivery(episode, _model("REFERENCE_CLONE"))
    assert manifest["publishable"] is False
    assert manifest["platforms"] == []
    assert not (episode / "delivery" / "publish" / "douyin.md").exists()


def test_delivery_manifest_is_idempotent(tmp_path: Path) -> None:
    episode = _episode(tmp_path)
    model = _model()
    first = run_delivery(episode, model)
    second = run_delivery(episode, model)
    assert first == second
