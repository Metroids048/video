"""Short-lived analysis media acquisition for the Whisper fallback."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .errors import ClassifiedError, classify_error


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class MediaResult:
    ok: bool
    path: Path | None = None
    error: ClassifiedError | None = None
    message: str = ""
    return_code: int | None = None
    started_at: str = ""
    ended_at: str = ""


class YtDlpMediaProvider:
    name = "yt-dlp-media"

    def __init__(self, *, runner: Callable[[list[str]], subprocess.CompletedProcess | object] | None = None,
                 timeout: int = 900, max_retries: int = 1):
        self.runner = runner or self._run
        self.timeout = timeout
        self.max_retries = max(0, min(max_retries, 1))

    def _run(self, command: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(command, capture_output=True, text=True, timeout=self.timeout, shell=False)

    def download(self, video_url: str, video_id: str, out_dir: Path) -> MediaResult:
        out_dir.mkdir(parents=True, exist_ok=True)
        started = _now()
        template = str(out_dir / f"{video_id}.analysis.%(ext)s")
        command = ["yt-dlp", "--no-playlist", "--no-warnings", "-f", "worstaudio/worst",
                   "--restrict-filenames", "-o", template, video_url]
        try:
            raw = self.runner(command)
            code = getattr(raw, "returncode", 0)
            stdout = str(getattr(raw, "stdout", "") or "")
            stderr = str(getattr(raw, "stderr", "") or "")
            if code:
                classified = classify_error(stderr or stdout, exit_code=code)
                if classified.retryable and self.max_retries:
                    raw = self.runner(command)
                    code = getattr(raw, "returncode", 0)
                    stdout = str(getattr(raw, "stdout", "") or "")
                    stderr = str(getattr(raw, "stderr", "") or "")
                    if not code:
                        classified = None
                    else:
                        classified = classify_error(stderr or stdout, exit_code=code)
                if classified is not None:
                    return MediaResult(False, error=classified, message=(stderr or stdout).strip()[:500],
                                       return_code=code, started_at=started, ended_at=_now())
        except subprocess.TimeoutExpired as exc:
            return MediaResult(False, error=ClassifiedError("NETWORK_TIMEOUT", True), message=str(exc),
                               started_at=started, ended_at=_now())
        except OSError as exc:
            return MediaResult(False, error=classify_error(str(exc)), message=str(exc), started_at=started, ended_at=_now())
        candidates = sorted(out_dir.glob(f"{video_id}.analysis.*"))
        candidates = [item for item in candidates if item.suffix.lower() not in {".part", ".ytdl"}]
        if not candidates:
            return MediaResult(False, error=ClassifiedError("MEDIA_FORMAT_UNAVAILABLE", False),
                               message="yt-dlp produced no analysis media", started_at=started, ended_at=_now())
        return MediaResult(True, path=candidates[0], started_at=started, ended_at=_now())
