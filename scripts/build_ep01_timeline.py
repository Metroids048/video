from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from avs.timeline.models import Canvas, Clip, Timeline, Track


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_ep01_timeline.py <episode-dir>")
    ep = Path(sys.argv[1]).resolve()
    scene_map = json.loads((ep / "work" / "final" / "scene-map.json").read_text(encoding="utf-8"))
    source = ep / "work" / "prepared" / "screen" / "原始录屏.mp4"
    if not source.is_file():
        raise FileNotFoundError(source)

    prepared_audio = ep / "work" / "prepared" / "audio" / "narration-final-48k.wav"
    prepared_audio.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ep / "work" / "audio" / "narration-final-48k.wav", prepared_audio)
    prepared_bgm = ep / "work" / "prepared" / "audio" / "bgm-tech-house.mp3"
    shutil.copy2(ep.parents[2] / "third_party_skills" / "video-shotcraft" / "assets" / "audio" / "bgm" / "bgm-tech-house.mp3", prepared_bgm)

    # EP01 is evidence-led screen documentary footage. Preserve the complete
    # landscape source page by default. Do not invent movement or crop away
    # left/right context merely to fill 9:16. Any future ROI crop must be a
    # separate, explicitly authorized semantic treatment after full context.
    video_clips: list[Clip] = []
    for index, shot in enumerate(scene_map):
        start = float(shot["output_start"])
        end = float(shot["output_end"])
        duration = end - start
        source_start = float(shot["source_start"])
        video_clips.append(
            Clip(
                clip_id=f"final-shot-{index:02d}",
                start=round(start, 3),
                duration=round(duration, 3),
                asset_ref="work/prepared/screen/原始录屏.mp4",
                in_point=source_start,
                out_point=source_start + duration,
                transform={"layout": "fit_full_frame"},
                primitive=None,
                segment_id=f"scene-{index:02d}",
                reference_pattern_ids=["single-primary-douyin-reference"],
            )
        )

    duration = float(scene_map[-1]["output_end"])
    timeline = Timeline(
        episode_id=ep.name,
        canvas=Canvas(width=1080, height=1920, fps=30.0),
        total_duration=duration,
        tracks=[
            Track(track_id="video-main", kind="video", clips=video_clips),
            Track(
                track_id="audio-voice",
                kind="audio",
                audio_role="voice",
                clips=[
                    Clip(
                        clip_id="narration-final",
                        start=0.0,
                        duration=duration,
                        asset_ref="work/prepared/audio/narration-final-48k.wav",
                        style={"role": "voice", "provider": "HYBRID_S2S", "volume": 1.0},
                    )
                ],
            ),
            Track(
                track_id="audio-bgm",
                kind="audio",
                audio_role="bgm",
                clips=[
                    Clip(
                        clip_id="bgm-tech-house",
                        start=0.0,
                        duration=duration,
                        asset_ref="work/prepared/audio/bgm-tech-house.mp3",
                        style={"role": "bgm", "volume": 0.08},
                    )
                ],
            ),
        ],
    )
    timeline_path = ep / "work" / "timeline.json"
    timeline.save(timeline_path)
    print(json.dumps({"timeline": str(timeline_path), "duration": duration, "shots": len(video_clips)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
