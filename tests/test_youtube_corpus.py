from __future__ import annotations

import json
from pathlib import Path

from avs.research.youtube.corpus import process_video, run_corpus, run_transcripts, transcript_gate


def _seed(tmp_path: Path) -> None:
    root = tmp_path
    (root / "channel.json").write_text(json.dumps({"title": "测试频道", "handle": "test", "canonical_url": "https://www.youtube.com/@test", "discovered_at": "2026-01-01T00:00:00Z", "extractor_version": "test"}, ensure_ascii=False), encoding="utf-8")
    row = {"video_id": "v1", "url": "https://www.youtube.com/watch?v=v1", "title": "测试视频", "duration": 10, "availability": "public", "extraction_status": "TRANSCRIPT_QA_PASSED"}
    (root / "catalog.jsonl").write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    (root / "corpus_manifest.json").write_text(json.dumps({"schema_version": "1.0", "channel_url": "https://www.youtube.com/@test", "generated_at": "2026-01-01T00:00:00Z", "extractor_version": "test", "provider": "test", "pagination_complete": True, "counts": {"discovered": 1, "unique_ids": 1, "unknown": 0, "TRANSCRIPT_QA_PASSED": 1}, "videos": [{"video_id": "v1", "status": "TRANSCRIPT_QA_PASSED", "attempts": []}], "attempts": []}), encoding="utf-8")
    transcript = {"video_id": "v1", "source_type": "MANUAL_CAPTION", "text": "如果突破 65000 点，观察支撑位置。", "segments": [{"segment_id": "SEG_0001", "start": 0, "end": 10, "text": "如果突破 65000 点，观察支撑位置。"}], "words": []}
    troot = root / "videos" / "v1" / "transcript"
    troot.mkdir(parents=True)
    (troot / "canonical.json").write_text(json.dumps(transcript, ensure_ascii=False), encoding="utf-8")
    (troot / "qa.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")


def test_content_pipeline_is_information_preserving_and_resumable(tmp_path: Path) -> None:
    _seed(tmp_path)
    result = process_video(tmp_path, json.loads((tmp_path / "catalog.jsonl").read_text()), resume=False)
    assert result["status"] in {"PASS", "UNAVAILABLE"}
    assert (tmp_path / "videos/v1/content.md").exists()
    assert (tmp_path / "videos/v1/semantic_units.jsonl").exists()
    assert (tmp_path / "videos/v1/source_map.json").exists()
    assert "65000" in (tmp_path / "videos/v1/content.md").read_text(encoding="utf-8")


def test_corpus_run_writes_progress_and_bundle(tmp_path: Path) -> None:
    _seed(tmp_path)
    result = run_corpus(tmp_path, resume=True)
    assert result["total"] == 1
    assert (tmp_path / "reports/progress.json").exists()
    assert (tmp_path / "reports/corpus-final.json").exists()
    assert (tmp_path / "agent_bundle/VIDEO_INDEX.md").exists()


def test_transcript_gate_does_not_count_blocked_as_terminal(tmp_path: Path) -> None:
    rows = []
    for index in range(275):
        rows.append({"video_id": f"v{index:03d}", "url": f"https://youtu.be/v{index:03d}",
                     "title": f"Video {index}", "extraction_status": "BLOCKED_BY_YOUTUBE"})
    rows[0]["extraction_status"] = "TRANSCRIPT_QA_PASSED"
    rows[-1]["extraction_status"] = "UNAVAILABLE"
    (tmp_path / "catalog.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    troot = tmp_path / "videos" / rows[0]["video_id"] / "transcript"
    troot.mkdir(parents=True)
    (troot / "canonical.json").write_text(json.dumps({"video_id": rows[0]["video_id"], "segments": []}), encoding="utf-8")
    (troot / "qa.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")

    gate = transcript_gate(tmp_path)

    assert gate["total"] == 275
    assert gate["transcript_passed"] == 1
    assert gate["blocked"] == 273
    assert gate["unavailable"] == 1
    assert gate["percentage"] == 0.3636
    assert gate["pass"] is False


def test_transcript_gate_passes_when_all_accessible_videos_have_transcripts(tmp_path: Path) -> None:
    rows = [{"video_id": f"v{index:03d}", "url": f"https://youtu.be/v{index:03d}",
             "extraction_status": "TRANSCRIPT_QA_PASSED"} for index in range(274)]
    rows.append({"video_id": "private", "url": "https://youtu.be/private", "extraction_status": "UNAVAILABLE"})
    (tmp_path / "catalog.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    for row in rows[:-1]:
        troot = tmp_path / "videos" / row["video_id"] / "transcript"
        troot.mkdir(parents=True)
        (troot / "canonical.json").write_text(json.dumps({"video_id": row["video_id"], "segments": []}), encoding="utf-8")
        (troot / "qa.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")

    gate = transcript_gate(tmp_path)

    assert gate["pass"] is True
    assert gate["transcript_passed"] == 274
    assert gate["accessible"] == 274


def test_transcript_scheduler_retries_blocked_and_skips_passed(tmp_path: Path, monkeypatch) -> None:
    _seed(tmp_path)
    blocked = {"video_id": "v2", "url": "https://youtu.be/v2", "title": "blocked", "extraction_status": "BLOCKED_BY_YOUTUBE"}
    rows = [json.loads(line) for line in (tmp_path / "catalog.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    (tmp_path / "catalog.jsonl").write_text("".join(json.dumps(row) + "\n" for row in [rows[0], blocked]), encoding="utf-8")
    calls: list[str] = []

    def fake_extract(root, video_id, **kwargs):
        calls.append(video_id)
        (root / "videos" / video_id / "transcript").mkdir(parents=True, exist_ok=True)
        (root / "videos" / video_id / "transcript" / "canonical.json").write_text(json.dumps({"video_id": video_id}), encoding="utf-8")
        (root / "videos" / video_id / "transcript" / "qa.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
        from avs.research.youtube.storage import update_video_state
        update_video_state(root, video_id, extraction_status="TRANSCRIPT_QA_PASSED")
        return {"video_id": video_id, "status": "PASS"}

    monkeypatch.setattr("avs.research.youtube.extraction.extract_transcript", fake_extract)
    result = run_transcripts(tmp_path, resume=True)

    assert calls == ["v2"]
    assert result["transcript_qa_passed"] == 2
    assert (tmp_path / "reports/transcript-progress.json").exists()
    assert (tmp_path / "TRANSCRIPT_INDEX.md").exists()
