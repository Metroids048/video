"""YouTube research discovery and corpus infrastructure."""

from .discovery import discover_channel
from .extraction import extract_transcript
from .models import ChannelRecord, VideoRecord
from .url import normalize_channel_url
from .clean import clean_video, clean_corpus_gate, normalize_text, plan_local_audio_repair
from .pipeline import run_research_pipeline

__all__ = ["ChannelRecord", "VideoRecord", "discover_channel", "extract_transcript", "normalize_channel_url",
           "clean_video", "clean_corpus_gate", "normalize_text", "plan_local_audio_repair", "run_research_pipeline"]
