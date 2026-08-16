"""Build the publishable V2 screen-documentary timeline.

This is intentionally episode-local: it changes the shot selection and layout
for the current recording without changing the shared renderer or source media.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EP = ROOT / "episodes" / "active" / "EP-20260812-01-V2"
SOURCE = "work/prepared/screen/20260812_131106.mp4"
VOICE_SOURCE = ROOT / "episodes" / "active" / "EP-20260812-01" / "work" / "prepared" / "audio" / "narration.m4a"


def clip(clip_id: str, start: float, duration: float, in_point: float, layout: str,
         primitive: str | None = None, region: list[float] | None = None) -> dict:
    transform = {"layout": layout}
    if region is not None:
        transform["region"] = region
    return {
        "clip_id": clip_id,
        "start": start,
        "duration": duration,
        "asset_ref": SOURCE,
        "in_point": in_point,
        "out_point": in_point + duration,
        "transform": transform,
        "text": None,
        "style": None,
        "primitive": primitive,
        "asset_id": "screen_20260812_131106",
        "region_id": None,
        "segment_id": clip_id,
        "evidence_id": None,
        "reference_pattern_ids": [],
        "keyframes": None,
    }


def main() -> None:
    old = json.loads((ROOT / "episodes" / "active" / "EP-20260812-01" / "work" / "timeline.json").read_text(encoding="utf-8"))
    captions = next(track for track in old["tracks"] if track["kind"] == "caption")
    # Keep the verified narration and captions, but remove all PPT-like graphics.
    voice = {
        "track_id": "audio-voice",
        "kind": "audio",
        "audio_role": "voice",
        "clips": [{
            "clip_id": "voice-narration",
            "start": 0.0,
            "duration": 76.9,
            "asset_ref": "work/prepared/audio/narration.m4a",
            "in_point": 0.0,
            "out_point": 76.9,
            "transform": None,
            "text": None,
            "style": {"role": "voice", "volume": 1.0},
            "primitive": None,
            "asset_id": None,
            "region_id": None,
            "segment_id": None,
            "evidence_id": None,
            "reference_pattern_ids": None,
            "keyframes": None,
        }],
    }
    video = {
        "track_id": "video-main",
        "kind": "video",
        "audio_role": None,
        "clips": [
            # Binance evidence opens the film. The whole page remains visible.
            clip("d-binance-balance-open", 0.0, 2.5, 129.0, "cover", "recording_focus_crop", [0.83, 0.54, 0.17, 0.43]),
            clip("d-binance-open", 2.5, 2.5, 129.0, "cover", "recording_focus_crop", [0.0, 0.42, 0.90, 0.54]),
            # Product overview: FIT, then let the viewer read the system.
            clip("d-dashboard-context", 5.0, 2.5, 1.0, "screen_focus"),
            clip("d-dashboard-detail", 7.5, 3.5, 1.0, "cover", "recording_focus_crop", [0.0, 0.04, 0.76, 0.28]),
            clip("d-research-context", 11.0, 3.0, 55.0, "screen_focus"),
            clip("d-research-detail", 14.0, 8.0, 55.0, "cover", "recording_focus_crop", [0.0, 0.10, 1.0, 0.28]),
            clip("d-decision-context", 22.0, 3.0, 68.0, "screen_focus"),
            clip("d-decision-detail", 25.0, 9.0, 68.0, "cover", "recording_focus_crop", [0.0, 0.08, 1.0, 0.78]),
            # The distinctive explanation page gets a controlled local punch-in.
            clip("d-why-no-trade", 34.0, 10.0, 84.0, "cover", "recording_focus_crop", [0.67, 0.22, 0.33, 0.54]),
            # Continuous exchange evidence: account/positions, then order history.
            clip("d-binance-positions", 44.0, 5.5, 129.0, "cover", "recording_focus_crop", [0.0, 0.38, 0.9, 0.55]),
            clip("d-binance-history", 49.5, 5.5, 136.0, "cover", "recording_focus_crop", [0.0, 0.42, 0.9, 0.54]),
            clip("d-binance-proof", 55.0, 10.0, 130.0, "screen_focus"),
            clip("d-dashboard-close-context", 65.0, 3.0, 156.0, "screen_focus"),
            clip("d-dashboard-close-detail", 68.0, 8.9, 156.0, "cover", "recording_focus_crop", [0.0, 0.46, 0.78, 0.50]),
        ],
    }
    timeline = {
        "episode_id": "EP-20260812-01-V2",
        "version": "2.0-d",
        "canvas": {"width": 1080, "height": 1920, "fps": 30.0},
        "total_duration": 76.9,
        "tracks": [video, captions, voice],
        "generated_at": "2026-08-12T00:00:00+00:00",
    }
    work = EP / "work"
    (work / "prepared" / "audio").mkdir(parents=True, exist_ok=True)
    shutil.copy2(VOICE_SOURCE, work / "prepared" / "audio" / "narration.m4a")
    (work / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    # Reuse the project caption segmentation rather than hand-writing a second SRT.
    sys.path.insert(0, str(ROOT / "src"))
    from avs.render.captions import build_srt
    from avs.timeline.models import Timeline
    build_srt(Timeline.load(work / "timeline.json"), work / "captions.srt")
    # Keep a human-readable shot note next to the protocol for review.
    (work / "final-shot-plan.md").write_text(
        "# V2 D final shot plan\n\n"
        "- 0-5s Binance Demo opening, whole screen FIT\n"
        "- 5-34s product overview, research, decision/risk FIT\n"
        "- 34-44s Why No Trade local PUNCH_IN\n"
        "- 44-65s Binance positions/order history/proof, continuous evidence\n"
        "- 65-76.9s dashboard close, FIT\n\n"
        "No generated cards, no logo end card, subtitles remain auxiliary.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
