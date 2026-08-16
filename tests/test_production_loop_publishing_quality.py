from pathlib import Path


def test_production_loop_requires_publishing_quality_not_just_technical_pass() -> None:
    prompt = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "creator-os"
        / "production-loop-prompt.md"
    ).read_text(encoding="utf-8")

    assert "TECHNICAL_BASELINE_PASS" in prompt
    assert "PUBLISHING_QUALITY_FAIL" in prompt
    assert "PUBLISHING_QUALITY_PASS" in prompt
    assert "First 10s" in prompt
    assert "result / anomaly" in prompt
    assert "human identity" in prompt
    assert "conflict" in prompt
    assert "low-information" in prompt
    assert "persistent course/PPT banner" in prompt
    assert "conversational" in prompt
    assert "next unresolved question" in prompt
    assert "Target duration: 45–60s" in prompt
    assert "Target duration: 55–65s" not in prompt
