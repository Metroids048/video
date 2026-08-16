from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_EP01_DURATION_SECONDS = 68.0
REQUIRED_SCORE_KEYS = {
    "hook",
    "story",
    "pacing",
    "evidence",
    "visual",
    "human_tone",
    "audio",
    "captions",
    "reference_fidelity",
    "overall",
}


def _resolve_inside_episode(ep: Path, relative: str) -> Path:
    path = (ep / relative).resolve()
    try:
        path.relative_to(ep)
    except ValueError as exc:
        raise ValueError(f"review artifact escapes episode: {relative}") from exc
    return path


def _probe_duration(video: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(video),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise ValueError(f"reviewed video is not ffprobe-decodable: {video}")
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise ValueError(f"invalid reviewed video duration: {result.stdout!r}") from exc


def _validate_review(ep: Path, payload: dict[str, Any]) -> dict[str, Any]:
    reviewer = payload.get("reviewer")
    if not isinstance(reviewer, dict):
        raise ValueError("reviewer provenance is required")
    if reviewer.get("mode") != "actual_artifact_review":
        raise ValueError("reviewer.mode must be actual_artifact_review; self-scoring is forbidden")
    if reviewer.get("inspected_pixels") is not True:
        raise ValueError("reviewer must explicitly confirm pixel inspection")
    if not str(reviewer.get("reviewer_id") or "").strip():
        raise ValueError("reviewer_id is required")

    reviewed_video = payload.get("reviewed_video")
    if not isinstance(reviewed_video, str) or not reviewed_video.strip():
        raise ValueError("reviewed_video is required")
    video_path = _resolve_inside_episode(ep, reviewed_video)
    if not video_path.is_file():
        raise ValueError(f"reviewed_video does not exist: {reviewed_video}")

    reviewed_artifacts = payload.get("reviewed_artifacts")
    if not isinstance(reviewed_artifacts, list) or not reviewed_artifacts:
        raise ValueError("reviewed_artifacts must contain inspected frame/contact-sheet evidence")
    for raw in reviewed_artifacts:
        if not isinstance(raw, str) or not _resolve_inside_episode(ep, raw).is_file():
            raise ValueError(f"review artifact does not exist: {raw}")

    scores = payload.get("scores")
    if not isinstance(scores, dict) or not REQUIRED_SCORE_KEYS.issubset(scores):
        missing = sorted(REQUIRED_SCORE_KEYS - set(scores or {}))
        raise ValueError(f"review scores are incomplete: {missing}")
    for name in REQUIRED_SCORE_KEYS:
        value = float(scores[name])
        if not 0.0 <= value <= 10.0:
            raise ValueError(f"score out of range: {name}={value}")

    if payload.get("passed") is not True or payload.get("blocked") is True:
        raise ValueError("review input did not pass")

    duration = _probe_duration(video_path)
    if duration > MAX_EP01_DURATION_SECONDS:
        raise ValueError(
            f"reviewed video is {duration:.3f}s; EP01 publish contract is <= {MAX_EP01_DURATION_SECONDS:.0f}s"
        )

    output = dict(payload)
    output["episode_id"] = ep.name
    output["duration_seconds"] = round(duration, 3)
    output["generated_at"] = datetime.now(timezone.utc).isoformat()
    output["validated_from"] = "work/qa/visual-review.input.json"
    return output


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: mark_ep01_visual_review.py <episode-dir>")

    ep = Path(sys.argv[1]).resolve()
    qa = ep / "work" / "qa"
    source = qa / "visual-review.input.json"
    if not source.is_file():
        raise SystemExit(
            "missing work/qa/visual-review.input.json; actual artifact review is mandatory and self-approval is forbidden"
        )

    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        validated = _validate_review(ep, payload)
    except (json.JSONDecodeError, OSError, TypeError, ValueError, subprocess.SubprocessError) as exc:
        raise SystemExit(f"visual review rejected: {exc}") from exc

    path = qa / "visual-review.json"
    path.write_text(json.dumps(validated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
