from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from avs.research.youtube.discovery import (
    discover_channel,
    normalize_channel_url,
)
from avs.research.youtube.errors import classify_error
from avs.research.youtube.models import VideoRecord
from avs.research.youtube.providers import (
    YtDlpFlatPlaylistProvider,
    YouTubeDataApiProvider,
)
from avs.research.youtube.storage import audit_corpus, load_catalog, write_corpus


def test_normalize_channel_url_handles_handle_and_query() -> None:
    normalized = normalize_channel_url("https://www.youtube.com/@qinxiongmao/?feature=shared")
    assert normalized.handle == "qinxiongmao"
    assert normalized.canonical_url == "https://www.youtube.com/@qinxiongmao"
    assert normalized.slug == "qinxiongmao"


def test_normalize_channel_url_rejects_non_channel() -> None:
    with pytest.raises(ValueError):
        normalize_channel_url("https://www.youtube.com/watch?v=abc")


def test_api_provider_paginates_and_batches_metadata() -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    def transport(endpoint: str, params: dict[str, str]) -> dict:
        calls.append((endpoint, params))
        if endpoint == "channels":
            return {
                "items": [{
                    "id": "UC123",
                    "snippet": {"title": "熊猫交易学社", "customUrl": "@qinxiongmao"},
                    "contentDetails": {"relatedPlaylists": {"uploads": "UU123"}},
                }]
            }
        if endpoint == "playlistItems" and params.get("pageToken") == "next":
            return {"items": [{"contentDetails": {"videoId": "vid2"}}]}
        if endpoint == "playlistItems":
            return {
                "nextPageToken": "next",
                "items": [{"contentDetails": {"videoId": "vid1"}}],
            }
        if endpoint == "videos":
            return {
                "items": [
                    {"id": "vid1", "snippet": {"title": "一", "publishedAt": "2026-01-01T00:00:00Z"},
                     "contentDetails": {"duration": "PT1M2S"}, "status": {"privacyStatus": "public"}},
                    {"id": "vid2", "snippet": {"title": "二"},
                     "contentDetails": {"duration": "PT2M"}, "status": {"privacyStatus": "public"}},
                ]
            }
        raise AssertionError(endpoint)

    result = YouTubeDataApiProvider("key", transport=transport).discover(
        "https://www.youtube.com/@qinxiongmao"
    )
    assert result.channel.channel_id == "UC123"
    assert [v.video_id for v in result.videos] == ["vid1", "vid2"]
    assert result.pagination_complete is True
    assert result.duplicates == 0
    assert any(endpoint == "playlistItems" and params.get("pageToken") == "next" for endpoint, params in calls)


def test_ytdlp_fixture_preserves_missing_metadata_as_null() -> None:
    payload = {
        "channel_id": "UC123",
        "channel": "熊猫交易学社",
        "uploader_url": "https://www.youtube.com/@qinxiongmao",
        "entries": [
            {"id": "vid1", "title": "视频一", "url": "vid1"},
            {"id": "vid1", "title": "重复", "url": "vid1"},
            {"id": "vid2", "title": "视频二", "url": "vid2", "duration": 12},
        ],
    }
    provider = YtDlpFlatPlaylistProvider(runner=lambda _: json.dumps(payload, ensure_ascii=False))
    result = provider.discover("https://www.youtube.com/@qinxiongmao")
    assert [v.video_id for v in result.videos] == ["vid1", "vid2"]
    assert result.videos[0].published_at is None
    assert result.videos[1].duration == 12
    assert result.duplicates == 1


def test_ytdlp_uses_videos_tab_for_channel_listing() -> None:
    seen: list[list[str]] = []
    payload = {"channel_id": "UC1", "channel": "Test", "entries": [{"id": "vid1", "title": "A"}]}
    provider = YtDlpFlatPlaylistProvider(runner=lambda command: (seen.append(command) or json.dumps(payload)))
    provider.discover("https://www.youtube.com/@test")
    assert seen[0][-1] == "https://www.youtube.com/@test/videos"


def test_api_failure_falls_back_to_ytdlp(tmp_path: Path) -> None:
    payload = {"channel_id": "UC1", "channel": "Test", "entries": [{"id": "vid1", "title": "A"}]}
    result = discover_channel(
        "https://www.youtube.com/@test",
        tmp_path,
        provider="auto",
        api_provider=YouTubeDataApiProvider("bad", transport=lambda *_: (_ for _ in ()).throw(RuntimeError("403"))),
        ytdlp_provider=YtDlpFlatPlaylistProvider(runner=lambda _: json.dumps(payload)),
    )
    assert result.provider == "yt-dlp"
    assert (tmp_path / "channel.json").is_file()


def test_write_corpus_is_idempotent_and_deduplicates(tmp_path: Path) -> None:
    first = VideoRecord(video_id="vid1", channel_id="UC1", title="A", url="https://youtu.be/vid1")
    write_corpus(tmp_path, channel={"source": "youtube", "channel_id": "UC1", "handle": "test",
                                    "title": "Test", "canonical_url": "https://www.youtube.com/@test",
                                    "uploads_playlist_id": "UU1", "discovered_at": "2026-08-22T00:00:00Z",
                                    "public_video_count": 1, "extractor_version": "test"},
                 videos=[first, first], provider="fixture")
    write_corpus(tmp_path, channel={"source": "youtube", "channel_id": "UC1", "handle": "test",
                                    "title": "Test", "canonical_url": "https://www.youtube.com/@test",
                                    "uploads_playlist_id": "UU1", "discovered_at": "2026-08-22T00:00:00Z",
                                    "public_video_count": 1, "extractor_version": "test"},
                 videos=[first], provider="fixture")
    assert len(load_catalog(tmp_path)) == 1
    manifest = json.loads((tmp_path / "corpus_manifest.json").read_text(encoding="utf-8"))
    assert manifest["counts"]["discovered"] == 1


def test_audit_detects_unknown_failure(tmp_path: Path) -> None:
    channel = {"source": "youtube", "channel_id": "UC1", "handle": "test", "title": "Test",
               "canonical_url": "https://www.youtube.com/@test", "uploads_playlist_id": "UU1",
               "discovered_at": "2026-08-22T00:00:00Z", "public_video_count": 1, "extractor_version": "test"}
    video = VideoRecord(video_id="vid1", channel_id="UC1", title="A", url="https://youtu.be/vid1",
                        extraction_status="FAILED_UNKNOWN")
    write_corpus(tmp_path, channel=channel, videos=[video], provider="fixture")
    report = audit_corpus(tmp_path)
    assert report.passed is False
    assert report.counts["FAILED_UNKNOWN"] == 1


def test_audit_enforces_count_conservation(tmp_path: Path) -> None:
    channel = {"source": "youtube", "channel_id": "UC1", "handle": "test", "title": "Test",
               "canonical_url": "https://www.youtube.com/@test", "uploads_playlist_id": "UU1",
               "discovered_at": "2026-08-22T00:00:00Z", "public_video_count": 1, "extractor_version": "test"}
    video = VideoRecord(video_id="vid1", channel_id="UC1", title="A", url="https://youtu.be/vid1")
    write_corpus(tmp_path, channel=channel, videos=[video], provider="fixture")
    path = tmp_path / "corpus_manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["counts"]["DISCOVERED"] = 0
    path.write_text(json.dumps(payload), encoding="utf-8")
    report = audit_corpus(tmp_path)
    assert report.passed is False
    assert "count_consistent" in report.errors


def test_error_classifier_is_bounded_and_specific() -> None:
    assert classify_error("HTTP Error 403: Forbidden").code == "HTTP_403"
    assert classify_error("Sign in to confirm you're not a bot").code == "SIGN_IN_CONFIRM_BOT"
    assert classify_error("Private video").code == "PRIVATE"
    assert classify_error("timed out").retryable is True


def test_research_schemas_validate_written_documents(tmp_path: Path) -> None:
    channel = {"source": "youtube", "channel_id": "UC1", "handle": "test", "title": "Test",
               "canonical_url": "https://www.youtube.com/@test", "uploads_playlist_id": "UU1",
               "discovered_at": "2026-08-22T00:00:00Z", "public_video_count": 1, "extractor_version": "test"}
    video = VideoRecord(video_id="vid1", channel_id="UC1", title="A", url="https://youtu.be/vid1")
    write_corpus(tmp_path, channel=channel, videos=[video], provider="fixture")
    schemas = Path(__file__).parents[1] / "schemas"
    for name in ("youtube-channel.schema.json", "youtube-corpus-manifest.schema.json"):
        schema = json.loads((schemas / name).read_text(encoding="utf-8"))
        payload = json.loads((tmp_path / ("channel.json" if "channel" in name else "corpus_manifest.json")).read_text(encoding="utf-8"))
        jsonschema.validate(payload, schema)
