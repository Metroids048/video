"""Channel URL normalization and provider orchestration."""
from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import replace
from pathlib import Path

from .errors import classify_error
from .models import AttemptRecord, DiscoveryResult
from .providers import YtDlpFlatPlaylistProvider, YouTubeDataApiProvider
from .storage import write_corpus
from .url import normalize_channel_url


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def discover_channel(
    channel_url: str,
    output_root: Path,
    *,
    provider: str = "auto",
    force: bool = False,
    api_key: str | None = None,
    api_provider: YouTubeDataApiProvider | None = None,
    ytdlp_provider: YtDlpFlatPlaylistProvider | None = None,
) -> DiscoveryResult:
    normalized = normalize_channel_url(channel_url)
    api = api_provider or (YouTubeDataApiProvider(api_key) if api_key else None)
    ytdlp = ytdlp_provider or YtDlpFlatPlaylistProvider()
    chosen = provider
    result: DiscoveryResult
    if provider not in {"auto", "api", "ytdlp"}:
        raise ValueError("provider 必须是 auto、api 或 ytdlp")
    if provider == "api" and api is None:
        raise ValueError("provider=api 需要 YOUTUBE_API_KEY")
    if provider == "ytdlp" or (provider == "auto" and api is None):
        chosen = "ytdlp"
        result = ytdlp.discover(normalized.canonical_url)
    else:
        chosen = "api"
        try:
            result = api.discover(normalized.canonical_url)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            if provider == "api" or not ytdlp:
                raise
            classified = classify_error(str(exc))
            safe_message = str(exc).replace(api.api_key if api else "", "***")
            result = ytdlp.discover(normalized.canonical_url)
            result.attempts.insert(0, AttemptRecord(
                provider="youtube-data-api", started_at=_now(), ended_at=_now(),
                error_code=classified.code, message=safe_message[:500],
                result="FALLBACK",
            ))
            chosen = "ytdlp"
    result = replace(result, provider=result.provider if result.provider else chosen)
    write_corpus(output_root, channel=result.channel.to_dict(), videos=result.videos,
                 provider=result.provider, pagination_complete=result.pagination_complete,
                 duplicates=result.duplicates, unknown_items=result.unknown_items,
                 attempts=result.attempts, force=force)
    return result
