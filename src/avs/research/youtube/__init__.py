"""YouTube research discovery and corpus infrastructure."""

from .discovery import discover_channel
from .extraction import extract_transcript
from .models import ChannelRecord, VideoRecord
from .url import normalize_channel_url

__all__ = ["ChannelRecord", "VideoRecord", "discover_channel", "extract_transcript", "normalize_channel_url"]
