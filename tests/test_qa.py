"""Deterministic QA report tests."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import jsonschema

from avs.qa.report import run_qa


def _episode(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    episode = project / "episodes" / "active" / "EP-QA-TEST"
    (project / "schemas").mkdir(parents=True)
    schema = Path(__file__).parents[1] / "schemas" / "qa-report.schema.json"
    shutil.copy2(schema, project / "schemas" / schema.name)
    for relative in ("renders", "work", "delivery"):
        (episode / relative).mkdir(parents=True, exist_ok=True)
    (episode / "renders" / "preview-clean.mp4").write_bytes(b"clean")
    (episode / "renders" / "preview-with-captions.mp4").write_bytes(b"captions")
    (episode / "work" / "timeline.json").write_text("{}", encoding="utf-8")
    (episode / "work" / "captions.srt").write_text("", encoding="utf-8")
    return episode


def _metadata(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "width": 1080, "height": 1920, "fps": 30.0, "duration": 9.0,
        "video_codec": "h264", "audio_codec": "aac", "has_audio": True,
        "size_bytes": 10,
    }
    payload.update(overrides)
    return payload


def _run(ep_dir: Path, *, publishable: bool = False, timeline: dict[str, object] | None = None, metadata: dict[str, object] | None = None, black: list[dict[str, float]] | None = None, silence: list[dict[str, float]] | None = None, peak: float | None = -6.0, subtitles: dict[str, object] | None = None) -> dict:
    timeline_result = timeline or {
        "errors": [], "warnings": [], "placeholder_count": 0,
        "planned_audio": False, "total_duration": 9.0,
    }
    subtitle_result = subtitles or {"missing": False, "overflow": [], "long_lines": []}

    def fake_contact(_video: Path, output: Path, _duration: float) -> Path:
        output.write_bytes(b"jpg")
        return output

    with (
        patch("avs.qa.report.inspect_timeline", return_value=timeline_result),
        patch("avs.qa.report.inspect_subtitles", return_value=subtitle_result),
        patch("avs.qa.report.probe_media", return_value=metadata or _metadata()),
        patch("avs.qa.report.decode_error", return_value=None),
        patch("avs.qa.report.detect_black_intervals", return_value=black or []),
        patch("avs.qa.report.detect_silence_intervals", return_value=silence or []),
        patch("avs.qa.report.detect_max_volume", return_value=peak),
        patch("avs.qa.report.create_final_contact_sheet", side_effect=fake_contact),
        patch("avs.qa.report._load_quality_config", return_value={}),
        patch("avs.qa.report.verify_approval_current", return_value=(not publishable, "测试无批准" if publishable else None)),
    ):
        return run_qa(ep_dir, "EP-QA-TEST", publishable=publishable, force=True)


def test_qa_checks_both_mp4s_and_writes_visual_artifacts(tmp_path: Path) -> None:
    """Test QA checks both MP4s and writes artifacts (publishable=False, no approval needed)."""
    episode = _episode(tmp_path)
    report = _run(episode, publishable=False)

    assert report["passed"] is True
    assert report["technical_passed"] is True
    assert report["human_approved"] is True  # Not required for non-publishable
    ids = {check["check_id"] for check in report["checks"]}
    assert {"clean_decode", "captions_decode", "black_frames", "audio_peak"} <= ids
    assert (episode / "delivery" / "qa-contact-sheet.jpg").is_file()
    assert (episode / "delivery" / "visual-review.md").is_file()
    schema = json.loads((Path(__file__).parents[1] / "schemas" / "qa-report.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(report)


def test_black_frame_over_one_second_fails_qa(tmp_path: Path) -> None:
    """Test black frames fail technical checks."""
    report = _run(_episode(tmp_path), publishable=False, black=[{"start": 1.0, "end": 2.2, "duration": 1.2}])
    assert report["passed"] is False
    assert report["technical_passed"] is False
    assert next(check for check in report["checks"] if check["check_id"] == "black_frames")["passed"] is False


def test_planned_audio_with_long_silence_fails_qa(tmp_path: Path) -> None:
    """Test planned audio with silence fails technical checks."""
    timeline = {"errors": [], "warnings": [], "placeholder_count": 0, "planned_audio": True, "total_duration": 9.0}
    silence = [{"start": 2.0, "end": 5.0, "duration": 3.0}]
    report = _run(_episode(tmp_path), publishable=False, timeline=timeline, silence=silence)
    assert report["passed"] is False
    assert report["technical_passed"] is False


def test_low_resolution_and_clipping_fail_qa(tmp_path: Path) -> None:
    """Test low resolution and clipping fail technical checks."""
    report = _run(_episode(tmp_path), publishable=False, metadata=_metadata(width=720, height=1280), peak=-0.2)
    failed = {check["check_id"] for check in report["checks"] if not check["passed"] and check["severity"] == "error"}
    assert {"clean_canvas", "captions_canvas", "audio_peak"} <= failed
    assert report["technical_passed"] is False


def test_subtitle_overflow_fails_but_placeholder_is_warning_for_non_publishable(tmp_path: Path) -> None:
    """Test subtitle overflow fails but placeholder is warning for non-publishable."""
    timeline = {"errors": [], "warnings": [], "placeholder_count": 2, "planned_audio": False, "total_duration": 9.0}
    subtitles = {"missing": False, "overflow": ["3"], "long_lines": []}
    report = _run(_episode(tmp_path), publishable=False, timeline=timeline, subtitles=subtitles)
    assert report["passed"] is False  # Due to subtitle overflow
    assert report["technical_passed"] is False
    placeholder = next(check for check in report["checks"] if check["check_id"] == "placeholder_assets")
    assert placeholder["severity"] == "warning"  # Not blocking for non-publishable


def test_placeholder_becomes_error_for_publishable(tmp_path: Path) -> None:
    """Test placeholders become error for publishable episodes."""
    timeline = {"errors": [], "warnings": [], "placeholder_count": 3, "planned_audio": False, "total_duration": 9.0}
    report = _run(_episode(tmp_path), publishable=True, timeline=timeline)
    placeholder = next(check for check in report["checks"] if check["check_id"] == "placeholder_assets")
    assert placeholder["severity"] == "error"
    assert report["publishability_passed"] is False
    assert "占位卡" in " ".join(report["blocking_reasons"])


def test_placeholder_warning_does_not_block_non_publishable_qa(tmp_path: Path) -> None:
    """Test placeholder warning does not block non-publishable QA."""
    timeline = {"errors": [], "warnings": [], "placeholder_count": 3, "planned_audio": False, "total_duration": 9.0}
    report = _run(_episode(tmp_path), publishable=False, timeline=timeline)
    assert report["passed"] is True
    assert report["technical_passed"] is True

