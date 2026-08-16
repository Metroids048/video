"""Legacy compatibility entrypoint for EP01 video review.

Creator OS V2.2 has one canonical video release gate for every episode.  This
script remains only so old commands fail safely instead of recreating a second
EP01-specific approval path.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from avs.qa.video_release import (  # noqa: E402
    REVIEW_INPUT_RELATIVE,
    VideoReleaseReviewError,
    save_video_release_review,
)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: mark_ep01_visual_review.py <episode-dir>")

    ep_dir = Path(sys.argv[1]).resolve()
    legacy_input = ep_dir / "work" / "qa" / "visual-review.input.json"
    canonical_input = ep_dir / REVIEW_INPUT_RELATIVE

    if legacy_input.is_file() and not canonical_input.is_file():
        raise SystemExit(
            "legacy work/qa/visual-review.input.json is no longer a release gate. "
            "Watch the CURRENT MP4 start-to-end at 1x and write "
            "work/qa/video-release-review.input.json, then run "
            "python scripts/validate_video_release_review.py <episode-dir>."
        )
    if not canonical_input.is_file():
        raise SystemExit(
            "missing work/qa/video-release-review.input.json; "
            "contact sheets/keyframes/metadata cannot replace a full 1x watch"
        )

    try:
        payload = json.loads(canonical_input.read_text(encoding="utf-8"))
        output_path = save_video_release_review(ep_dir, payload)
        output = json.loads(output_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, TypeError, ValueError, VideoReleaseReviewError) as exc:
        raise SystemExit(f"video release review rejected: {exc}") from exc

    print(
        "DEPRECATED: mark_ep01_visual_review.py now delegates to the canonical "
        "Creator OS video release gate."
    )
    print(output_path)
    if output.get("final_status") != "READY_TO_PUBLISH":
        print("release gate not ready; repair/rerender/full rewatch required")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
