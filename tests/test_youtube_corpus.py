from __future__ import annotations

import json
from pathlib import Path

from avs.research.youtube.corpus import process_video, run_corpus


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
