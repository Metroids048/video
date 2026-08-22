"""Discovery providers: YouTube Data API and yt-dlp flat playlist."""
from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .errors import classify_error
from .models import (
    AttemptRecord,
    ChannelRecord,
    DiscoveryResult,
    ExtractionStatus,
    VideoRecord,
)
from .url import normalize_channel_url


class DiscoveryProvider(Protocol):
    name: str

    def discover(self, channel_url: str) -> DiscoveryResult: ...


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _duration_seconds(value: str | None) -> float | None:
    if not value:
        return None
    match = re.fullmatch(r"P(?:([0-9]+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", value)
    if not match:
        return None
    days, hours, minutes, seconds = match.groups()
    return float(days or 0) * 86400 + float(hours or 0) * 3600 + float(minutes or 0) * 60 + float(seconds or 0)


class YouTubeDataApiProvider:
    name = "youtube-data-api"

    def __init__(self, api_key: str, *, transport: Callable[[str, dict[str, str]], dict[str, Any]] | None = None):
        self.api_key = api_key
        self.transport = transport or self._request

    def _request(self, endpoint: str, params: dict[str, str]) -> dict[str, Any]:
        query = dict(params)
        query["key"] = self.api_key
        url = "https://www.googleapis.com/youtube/v3/" + endpoint + "?" + urlencode(query)
        request = Request(url, headers={"User-Agent": "avs-youtube-research/0.1"})
        with urlopen(request, timeout=30) as response:  # noqa: S310 - user-configured public endpoint
            return json.loads(response.read().decode("utf-8"))

    def discover(self, channel_url: str) -> DiscoveryResult:
        normalized = normalize_channel_url(channel_url)
        started = _now()
        params: dict[str, str] = {"part": "snippet,contentDetails", "maxResults": "1"}
        if normalized.channel_id:
            params["id"] = normalized.channel_id
        elif normalized.handle:
            params["forHandle"] = "@" + normalized.handle
        else:
            raise ValueError("YouTube Data API 需要 channel_id 或 handle")
        payload = self.transport("channels", params)
        items = payload.get("items") or []
        if not items:
            raise RuntimeError("channel not found")
        channel = items[0]
        snippet = channel.get("snippet") or {}
        content = channel.get("contentDetails") or {}
        channel_id = channel.get("id") or normalized.channel_id
        handle = snippet.get("customUrl") or normalized.handle
        if handle and handle.startswith("@"):
            handle = handle[1:]
        canonical = f"https://www.youtube.com/@{handle}" if handle else f"https://www.youtube.com/channel/{channel_id}"
        discovered_at = _now()
        playlist_id = (content.get("relatedPlaylists") or {}).get("uploads")
        video_ids: list[str] = []
        duplicate_count = 0
        page_token: str | None = None
        pagination_complete = True
        while True:
            page_params = {"part": "snippet,contentDetails", "playlistId": playlist_id or "", "maxResults": "50"}
            if page_token:
                page_params["pageToken"] = page_token
            page = self.transport("playlistItems", page_params)
            for item in page.get("items") or []:
                video_id = ((item.get("contentDetails") or {}).get("videoId") or
                            ((item.get("snippet") or {}).get("resourceId") or {}).get("videoId"))
                if not video_id:
                    continue
                if video_id in video_ids:
                    duplicate_count += 1
                else:
                    video_ids.append(video_id)
            page_token = page.get("nextPageToken")
            if not page_token:
                break
        videos: list[VideoRecord] = []
        for offset in range(0, len(video_ids), 50):
            batch = video_ids[offset:offset + 50]
            metadata = self.transport("videos", {"part": "snippet,contentDetails,status,liveStreamingDetails",
                                                  "id": ",".join(batch), "maxResults": "50"})
            by_id = {item.get("id"): item for item in metadata.get("items") or []}
            for video_id in batch:
                item = by_id.get(video_id) or {}
                item_snippet = item.get("snippet") or {}
                item_content = item.get("contentDetails") or {}
                item_status = item.get("status") or {}
                availability = item_status.get("privacyStatus") or "public"
                status = ExtractionStatus.DISCOVERED.value
                if availability == "private":
                    status = ExtractionStatus.PRIVATE.value
                videos.append(VideoRecord(
                    video_id=video_id,
                    channel_id=channel_id,
                    title=item_snippet.get("title"),
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    description=item_snippet.get("description"),
                    published_at=item_snippet.get("publishedAt"),
                    duration=_duration_seconds(item_content.get("duration")),
                    availability=availability,
                    live_status=(item.get("liveStreamingDetails") and "live") or "not_live",
                    thumbnail=((item_snippet.get("thumbnails") or {}).get("high") or
                               (item_snippet.get("thumbnails") or {}).get("default") or {}).get("url"),
                    discovered_at=discovered_at,
                    extraction_status=status,
                ))
        channel_record = ChannelRecord(
            source="youtube", channel_id=channel_id, handle=handle,
            title=snippet.get("title"), canonical_url=canonical,
            uploads_playlist_id=playlist_id, discovered_at=discovered_at,
            public_video_count=len(videos), extractor_version="youtube-research/0.1",
        )
        return DiscoveryResult(
            channel=channel_record, videos=videos, provider=self.name,
            pagination_complete=pagination_complete, duplicates=duplicate_count,
            attempts=[AttemptRecord(self.name, started, _now(), result="OK")],
        )


class YtDlpFlatPlaylistProvider:
    name = "yt-dlp"

    def __init__(self, *, runner: Callable[[list[str]], str] | None = None):
        self.runner = runner or self._run

    @staticmethod
    def _run(command: list[str]) -> str:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=120)
        if proc.returncode:
            raise RuntimeError((proc.stderr or proc.stdout or "yt-dlp failed").strip())
        return proc.stdout

    def discover(self, channel_url: str) -> DiscoveryResult:
        normalized = normalize_channel_url(channel_url)
        started = _now()
        listing_url = normalized.canonical_url.rstrip("/") + "/videos"
        command = ["yt-dlp", "--flat-playlist", "--dump-single-json", "--skip-download", "--no-warnings", listing_url]
        raw = self.runner(command)
        payload = json.loads(raw)
        entries = payload.get("entries") or []
        videos: list[VideoRecord] = []
        seen: set[str] = set()
        duplicates = 0
        for entry in entries:
            if not entry:
                continue
            video_id = entry.get("id")
            if not video_id:
                continue
            if video_id in seen:
                duplicates += 1
                continue
            seen.add(video_id)
            availability = entry.get("availability") or "public"
            status = ExtractionStatus.DISCOVERED.value
            if availability == "private":
                status = ExtractionStatus.PRIVATE.value
            videos.append(VideoRecord(
                video_id=video_id,
                channel_id=payload.get("channel_id") or entry.get("channel_id"),
                title=entry.get("title"),
                url=entry.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}",
                description=entry.get("description"),
                published_at=entry.get("upload_date"),
                duration=entry.get("duration"),
                availability=availability,
                live_status=entry.get("live_status"),
                thumbnail=entry.get("thumbnail"),
                discovered_at=_now(),
                extraction_status=status,
            ))
        handle = normalized.handle or payload.get("uploader_id")
        canonical = normalized.canonical_url
        channel = ChannelRecord(
            source="youtube", channel_id=payload.get("channel_id"), handle=handle,
            title=payload.get("channel") or payload.get("uploader"), canonical_url=canonical,
            uploads_playlist_id=None, discovered_at=_now(), public_video_count=len(videos),
            extractor_version="youtube-research/0.1",
        )
        return DiscoveryResult(
            channel=channel, videos=videos, provider=self.name,
            pagination_complete=True, duplicates=duplicates,
            attempts=[AttemptRecord(self.name, started, _now(), result="OK")],
        )
