"""YouTube channel URL normalization."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from .models import NormalizedChannelURL


def normalize_channel_url(value: str) -> NormalizedChannelURL:
    raw = value.strip()
    if raw.startswith("@"):
        raw = "https://www.youtube.com/" + raw
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        raise ValueError(f"不是 YouTube 频道 URL: {value}")
    parts = [p for p in parsed.path.split("/") if p]
    handle: str | None = None
    channel_id: str | None = None
    if parts and parts[0].startswith("@"):
        handle = parts[0][1:]
        if not re.fullmatch(r"[A-Za-z0-9._-]+", handle):
            raise ValueError(f"非法 YouTube handle: {handle}")
        canonical = f"https://www.youtube.com/@{handle}"
        slug = handle.lower()
    elif len(parts) >= 2 and parts[0] == "channel":
        channel_id = parts[1]
        canonical = f"https://www.youtube.com/channel/{channel_id}"
        slug = f"channel_{channel_id}"
    else:
        raise ValueError("仅支持 /@handle 或 /channel/<id> 频道 URL")
    return NormalizedChannelURL(value, canonical, handle, channel_id, slug)

