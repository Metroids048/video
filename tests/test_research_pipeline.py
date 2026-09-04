from __future__ import annotations

import json
from pathlib import Path

from avs.research.youtube.pipeline import run_research_pipeline
from avs.research.youtube.clean import normalize_text


def _seed(root: Path) -> None:
    (root / "channel.json").write_text(json.dumps({"title": "熊猫交易学社"}, ensure_ascii=False), encoding="utf-8")
    row = {"video_id": "v1", "title": "斐波那契与道氏理论", "extraction_status": "TRANSCRIPT_QA_PASSED"}
    (root / "catalog.jsonl").write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    troot = root / "videos" / "v1" / "transcript"
    troot.mkdir(parents=True)
    canonical = {"video_id": "v1", "source_type": "MANUAL_CAPTION", "segments": [
        {"segment_id": "SEG_0001", "start": 0, "end": 3, "text": "如果 突破 钱高，止损放在钱低。"},
        {"segment_id": "SEG_0002", "start": 3, "end": 6, "text": "观察肺胖大气 0. 38 2 回撤。"},
    ]}
    canonical["text"] = " ".join(s["text"] for s in canonical["segments"])
    (troot / "canonical.json").write_text(json.dumps(canonical, ensure_ascii=False), encoding="utf-8")
    (troot / "qa.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")


def test_normalize_text_preserves_ascii_tokens() -> None:
    value = normalize_text("BTC 1 H 0. 38 2 回撤 58, 000")
    assert "BTC 1H" in value and "0.382" in value and "58,000" in value


def test_pipeline_writes_layered_artifacts_and_no_promotable_strategy(tmp_path: Path) -> None:
    _seed(tmp_path)
    result = run_research_pipeline(tmp_path)
    state = result["state"]
    assert state["clean_corpus"]["status"] == "PASS"
    assert state["agent_corpus"]["status"] == "PASS"
    assert state["rule_compilation"]["status"] == "NO_PROMOTABLE_STRATEGY"
    assert state["quant_research"]["status"] == "NO_PROMOTABLE_STRATEGY"
    assert state["quant_research"]["promotion_authorized"] is False
    clean = json.loads((tmp_path / "videos/v1/clean/cleaned.json").read_text(encoding="utf-8"))
    assert "前高" in clean["text"] and "前低" in clean["text"] and "斐波那契" in clean["text"]
    assert (tmp_path / "agent_corpus/README.md").exists()
    assert "agent_bundle" not in (tmp_path / "README_FOR_AGENTS.md").read_text(encoding="utf-8")


def test_terminal_unavailable_rows_do_not_fake_a_clean_pass(tmp_path: Path) -> None:
    _seed(tmp_path)
    with (tmp_path / "catalog.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"video_id": "private", "title": "不可用", "extraction_status": "UNAVAILABLE"}, ensure_ascii=False) + "\n")
    result = run_research_pipeline(tmp_path)
    assert result["state"]["clean_corpus"]["status"] == "PASS"
    assert result["state"]["clean_corpus"]["accessible"] == 1


def test_semantic_asr_suspects_block_clean_gate(tmp_path: Path) -> None:
    _seed(tmp_path)
    canonical_path = tmp_path / "videos/v1/transcript/canonical.json"
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    canonical["segments"][0]["text"] = "航行分析课里讲裸 ks b 结构，关键为要等信号。"
    canonical["text"] = " ".join(s["text"] for s in canonical["segments"])
    canonical_path.write_text(json.dumps(canonical, ensure_ascii=False), encoding="utf-8")

    result = run_research_pipeline(tmp_path, resume=False)

    assert result["state"]["clean_corpus"]["status"] == "FAIL"
    qa = json.loads((tmp_path / "videos/v1/clean/clean_qa.json").read_text(encoding="utf-8"))
    assert qa["semantic_status"] == "REVIEW_REQUIRED"
    assert qa["semantic_issue_count"] >= 1
    assert (tmp_path / "clean_corpus/semantic-review.jsonl").exists()


def test_semantic_clean_failure_stops_knowledge_build(tmp_path: Path) -> None:
    _seed(tmp_path)
    canonical_path = tmp_path / "videos/v1/transcript/canonical.json"
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    canonical["segments"][0]["text"] = "裸 ks b 结构仍然需要人工核对。"
    canonical["text"] = " ".join(s["text"] for s in canonical["segments"])
    canonical_path.write_text(json.dumps(canonical, ensure_ascii=False), encoding="utf-8")

    result = run_research_pipeline(tmp_path, resume=False)

    assert result["state"]["agent_corpus"]["status"] == "WAITING_FOR_INPUT"
    assert not (tmp_path / "videos/v1/knowledge/knowledge_qa.json").exists()
