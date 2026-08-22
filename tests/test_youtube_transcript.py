from __future__ import annotations

import json
import subprocess
from pathlib import Path

from avs.research.youtube.asr import ASRResult, FasterWhisperProvider
from avs.research.youtube.captions import CaptionResult, YtDlpCaptionProvider
from avs.research.youtube.extraction import extract_transcript
from avs.research.youtube.media import MediaResult
from avs.research.youtube.models import VideoRecord
from avs.research.youtube.storage import load_catalog, write_corpus
from avs.research.youtube.transcript import TranscriptSegment, canonical_from_whisper, parse_vtt
from avs.research.youtube.transcript_quality import assess_transcript


def _seed(root: Path, *, duration: float | None = 120) -> None:
    channel = {"source": "youtube", "channel_id": "UC1", "handle": "test", "title": "Test",
               "canonical_url": "https://www.youtube.com/@test", "uploads_playlist_id": "UU1",
               "discovered_at": "2026-08-22T00:00:00Z", "public_video_count": 1,
               "extractor_version": "test"}
    write_corpus(root, channel=channel, videos=[VideoRecord(video_id="v1", channel_id="UC1", title="A",
                       url="https://www.youtube.com/watch?v=v1", duration=duration)], provider="fixture")


def test_vtt_parser_normalizes_timestamp_and_html() -> None:
    language, segments = parse_vtt("WEBVTT LANGUAGE=zh-Hans\n\n00:00:01.000 --> 00:00:02.250\n<b>这里</b>  有线\n")
    assert language == "zh-Hans"
    assert segments[0].start == 1
    assert segments[0].end == 2.25
    assert segments[0].text == "这里 有线"


def test_caption_provider_manual_precedes_auto(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def runner(command: list[str]):
        calls.append(command)
        out = Path(command[command.index("-o") + 1].replace("%(ext)s", "vtt"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:10.000\n人工字幕内容足够长\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    result = YtDlpCaptionProvider(runner=runner).fetch("https://youtu.be/v1", "v1", tmp_path)
    assert result.ok is True
    assert result.source_type == "MANUAL_CAPTION"
    assert len(calls) == 1


def test_caption_provider_prefers_simplified_chinese_over_english(tmp_path: Path) -> None:
    def runner(command: list[str]):
        out = Path(command[command.index("-o") + 1])
        base = out.parent
        base.mkdir(parents=True, exist_ok=True)
        (base / "v1.en.vtt").write_text("WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nEnglish text here\n", encoding="utf-8")
        (base / "v1.zh-Hans.vtt").write_text("WEBVTT\n\n00:00:00.000 --> 00:00:02.000\n中文字幕内容足够长\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    result = YtDlpCaptionProvider(runner=runner).fetch("https://youtu.be/v1", "v1", tmp_path)
    assert result.ok is True
    assert result.language == "zh-Hans"


def test_caption_failure_falls_back_to_asr_and_keeps_words(tmp_path: Path) -> None:
    _seed(tmp_path)

    class Captions:
        def fetch(self, *args, **kwargs):
            return CaptionResult(False, error=type("E", (), {"code": "CAPTION_UNAVAILABLE", "blocked": False, "retryable": False})(),
                                 message="no captions", started_at="a", ended_at="b", attempts=[{"provider": "caption", "result": "CAPTION_UNAVAILABLE"}])

    class Media:
        def download(self, *args, **kwargs):
            path = tmp_path / "media" / "v1.analysis.m4a"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture")
            return MediaResult(True, path=path, started_at="a", ended_at="b")

    def fake_transcribe(*args, **kwargs):
        return {"language_code": "zh", "segments": [{"start": 0, "end": 12, "text": "中文交易说明"}],
                "words": [{"type": "word", "text": "中文", "start": 0, "end": 1},
                          {"type": "word", "text": "交易", "start": 1, "end": 2}]}

    result = extract_transcript(tmp_path, "v1", caption_provider=Captions(), media_provider=Media(),
                               asr_provider=FasterWhisperProvider(transcriber=fake_transcribe))
    assert result["status"] == "PASS"
    assert result["source_type"] == "ASR_WHISPER"
    canonical = json.loads((tmp_path / "videos/v1/transcript/canonical.json").read_text(encoding="utf-8"))
    assert canonical["words"][0]["text"] == "中文"
    assert load_catalog(tmp_path)[0]["extraction_status"] == "TRANSCRIPT_QA_PASSED"


def test_bad_caption_quality_falls_back_to_asr(tmp_path: Path) -> None:
    _seed(tmp_path, duration=300)

    class Captions:
        def fetch(self, *args, **kwargs):
            segments = [TranscriptSegment("x", 0, 1, "重复")]
            return CaptionResult(True, "AUTO_CAPTION", "zh", tmp_path / "bad.vtt", segments,
                                 started_at="a", ended_at="b", attempts=[{"provider": "caption", "result": "CAPTION_OK"}])

    class Media:
        def download(self, *args, **kwargs):
            path = tmp_path / "media" / "v1.analysis.m4a"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture")
            return MediaResult(True, path=path)

    asr = FasterWhisperProvider(transcriber=lambda *a, **k: {"language_code": "zh", "segments": [{"start": 0, "end": 240, "text": "足够长的语音内容"}], "words": []})
    result = extract_transcript(tmp_path, "v1", caption_provider=Captions(), media_provider=Media(), asr_provider=asr)
    assert result["source_type"] == "ASR_WHISPER"


def test_resume_skips_qa_passed_without_provider_calls(tmp_path: Path) -> None:
    _seed(tmp_path, duration=10)

    class Captions:
        calls = 0
        def fetch(self, *args, **kwargs):
            self.calls += 1
            return CaptionResult(True, "MANUAL_CAPTION", "zh", None,
                                 [TranscriptSegment("x", 0, 10, "这是一段足够长的人工字幕内容")], attempts=[])

    provider = Captions()
    first = extract_transcript(tmp_path, "v1", caption_provider=provider)
    second = extract_transcript(tmp_path, "v1", caption_provider=provider)
    assert first["status"] == "PASS"
    assert second["status"] == "SKIPPED"
    assert provider.calls == 1


def test_whisper_canonical_preserves_word_timestamps() -> None:
    canonical = canonical_from_whisper("v1", {"language_code": "zh", "words": [
        {"type": "word", "text": "你好", "start": 1.2, "end": 1.8},
        {"type": "spacing", "text": " ", "start": 1.8, "end": 2.0},
    ]})
    assert canonical.words[0].start == 1.2
    assert canonical.segments[0].start == 1.2


def test_quality_gate_flags_empty_and_short_transcript() -> None:
    transcript = canonical_from_whisper("v1", {"language_code": "zh", "words": []})
    qa = assess_transcript(transcript, duration=100)
    assert qa.status == "FAIL"
    assert "EMPTY_TEXT" in qa.reasons
