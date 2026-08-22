"""Typed records for the YouTube research corpus discovery layer."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class ExtractionStatus(StrEnum):
    DISCOVERED = "DISCOVERED"
    PRIVATE = "PRIVATE"
    DELETED = "DELETED"
    UNAVAILABLE = "UNAVAILABLE"
    BLOCKED_BY_YOUTUBE = "BLOCKED_BY_YOUTUBE"
    RETRYABLE_FAILED = "RETRYABLE_FAILED"
    FAILED_UNKNOWN = "FAILED_UNKNOWN"
    CAPTION_PENDING = "CAPTION_PENDING"
    CAPTION_OK = "CAPTION_OK"
    CAPTION_UNAVAILABLE = "CAPTION_UNAVAILABLE"
    MEDIA_PENDING = "MEDIA_PENDING"
    MEDIA_OK = "MEDIA_OK"
    ASR_PENDING = "ASR_PENDING"
    ASR_OK = "ASR_OK"
    TRANSCRIPT_NORMALIZED = "TRANSCRIPT_NORMALIZED"
    TRANSCRIPT_QA_PASSED = "TRANSCRIPT_QA_PASSED"
    VISUAL_EVIDENCE = "VISUAL_EVIDENCE"
    VISUAL_QA_PASSED = "VISUAL_QA_PASSED"
    SEMANTIC_EXTRACTION = "SEMANTIC_EXTRACTION"
    CONTENT_BUILD = "CONTENT_BUILD"
    CONTENT_QA = "CONTENT_QA"
    CONTENT_QA_PASSED = "CONTENT_QA_PASSED"


TERMINAL_STATUSES = {
    ExtractionStatus.DISCOVERED.value,
    ExtractionStatus.PRIVATE.value,
    ExtractionStatus.DELETED.value,
    ExtractionStatus.UNAVAILABLE.value,
    ExtractionStatus.BLOCKED_BY_YOUTUBE.value,
    ExtractionStatus.RETRYABLE_FAILED.value,
    ExtractionStatus.FAILED_UNKNOWN.value,
    ExtractionStatus.CAPTION_PENDING.value,
    ExtractionStatus.CAPTION_OK.value,
    ExtractionStatus.CAPTION_UNAVAILABLE.value,
    ExtractionStatus.MEDIA_PENDING.value,
    ExtractionStatus.MEDIA_OK.value,
    ExtractionStatus.ASR_PENDING.value,
    ExtractionStatus.ASR_OK.value,
    ExtractionStatus.TRANSCRIPT_NORMALIZED.value,
    ExtractionStatus.TRANSCRIPT_QA_PASSED.value,
    ExtractionStatus.VISUAL_EVIDENCE.value,
    ExtractionStatus.VISUAL_QA_PASSED.value,
    ExtractionStatus.SEMANTIC_EXTRACTION.value,
    ExtractionStatus.CONTENT_BUILD.value,
    ExtractionStatus.CONTENT_QA.value,
    ExtractionStatus.CONTENT_QA_PASSED.value,
}


@dataclass(frozen=True)
class NormalizedChannelURL:
    original_url: str
    canonical_url: str
    handle: str | None
    channel_id: str | None
    slug: str


@dataclass
class ChannelRecord:
    source: str
    channel_id: str | None
    handle: str | None
    title: str | None
    canonical_url: str
    uploads_playlist_id: str | None
    discovered_at: str
    public_video_count: int
    extractor_version: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AttemptRecord:
    provider: str
    started_at: str
    ended_at: str
    exit_code: int | None = None
    error_code: str | None = None
    message: str | None = None
    result: str = "OK"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VideoRecord:
    video_id: str
    channel_id: str | None
    title: str | None
    url: str
    description: str | None = None
    published_at: str | None = None
    duration: float | None = None
    availability: str = "public"
    live_status: str | None = None
    thumbnail: str | None = None
    discovered_at: str | None = None
    extraction_status: str = ExtractionStatus.DISCOVERED.value
    attempts: list[AttemptRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["attempts"] = [a.to_dict() if isinstance(a, AttemptRecord) else a for a in self.attempts]
        return payload


@dataclass
class DiscoveryResult:
    channel: ChannelRecord
    videos: list[VideoRecord]
    provider: str
    pagination_complete: bool
    duplicates: int = 0
    unknown_items: int = 0
    attempts: list[AttemptRecord] = field(default_factory=list)


@dataclass
class AuditReport:
    passed: bool
    checks: dict[str, bool]
    counts: dict[str, int]
    errors: list[str] = field(default_factory=list)
