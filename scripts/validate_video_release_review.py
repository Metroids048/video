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
        raise SystemExit("usage: validate_video_release_review.py <episode-dir>")

    ep_dir = Path(sys.argv[1]).resolve()
    source = ep_dir / REVIEW_INPUT_RELATIVE
    if not source.is_file():
        raise SystemExit(
            "missing work/qa/video-release-review.input.json; "
            "必须先对当前成片执行完整 1x 连续观看、首10秒密集检查、全部转场检查、"
            "360x640 移动端检查并完整听音频"
        )

    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        output_path = save_video_release_review(ep_dir, payload)
        output = json.loads(output_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, TypeError, VideoReleaseReviewError, ValueError) as exc:
        raise SystemExit(f"video release review rejected: {exc}") from exc

    print(output_path)
    status = output.get("final_status")
    if status != "READY_TO_PUBLISH":
        print(f"release gate: {status}; 必须先修复并重新渲染、重新完整验收")
        return 2

    print("release gate: READY_TO_PUBLISH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
