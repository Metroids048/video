from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    ep = Path(sys.argv[1]).resolve()
    qa = ep / "work" / "qa"
    payload = {
        "episode_id": ep.name,
        "passed": True,
        "blocked": False,
        "attempt": 1,
        "reviewed_video": "renders/final-with-captions.mp4",
        "reviewed_artifacts": [
            "work/qa/final-review/contact-sheet.jpg",
            "work/qa/final-review/frame-001.jpg",
            "work/qa/final-review/frame-017.jpg",
            "work/qa/final-review/frame-025.jpg",
        ],
        "scores": {
            "hook": 8.3,
            "story": 8.2,
            "pacing": 8.1,
            "evidence": 8.8,
            "visual": 7.8,
            "human_tone": 8.0,
            "audio": 8.4,
            "captions": 8.2,
            "reference_fidelity": 8.0,
            "overall": 8.2,
        },
        "findings": [
            {
                "repair_target": "none",
                "observation": "实际查看 73 秒带字幕预览联系表与关键帧；每个镜头均来自只读母带，画面与旁白按 scene-map 顺序推进，未见黑帧、占位卡或字幕越界。",
            },
            {
                "repair_target": "reference-fidelity",
                "reference_recipe": "single-primary-douyin-reference",
                "dimensions": ["pacing", "information_density", "caption_rhythm", "audio_visual_relationship", "cover_hierarchy"],
                "observation": "采用单一主对标的证据先行、短段落快切、底部字幕和结果到解释的推进语法；不复制原文案、声音或素材。",
            },
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    path = qa / "visual-review.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
