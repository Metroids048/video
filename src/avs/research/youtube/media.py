"""Short-lived analysis media acquisition for the Whisper fallback."""
from __future__ import annotations

import subprocess
import json
import os
import time
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


class BrowserProfileMediaProvider:
    """Capture the real YouTube audio from a logged-in browser profile.

    The browser is deliberately a single-worker, opt-in fallback.  It never
    reads a cookie database; the browser profile remains outside the repo and
    is selected with ``AVS_BROWSER_PROFILE_DIR``.
    """

    name = "browser-profile-media-capture"

    def __init__(self, *, runner: Callable[[list[str]], subprocess.CompletedProcess | object] | None = None,
                 timeout: int = 3600, segment_seconds: int = 90):
        self.runner = runner or self._run
        self.timeout = timeout
        self.segment_seconds = max(15, int(segment_seconds))

    def _run(self, command: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(command, capture_output=True, text=True, timeout=self.timeout, shell=False)

    @staticmethod
    def _error(code: str, message: str = "") -> ClassifiedError:
        if code in {"PRIVATE", "DELETED", "UNAVAILABLE"}:
            return ClassifiedError(code, False)
        return ClassifiedError(code or "BROWSER_CAPTURE_FAILED", True, code in {
            "SIGN_IN_CONFIRM_BOT", "LOGIN_REQUIRED", "PO_TOKEN_REQUIRED", "HTTP_403", "IP_BLOCKED",
        })

    def download(self, video_url: str, video_id: str, out_dir: Path) -> MediaResult:
        out_dir.mkdir(parents=True, exist_ok=True)
        started = _now()
        profile_dir = os.environ.get("AVS_BROWSER_PROFILE_DIR")
        if not profile_dir:
            error = self._error("BROWSER_PROFILE_UNAVAILABLE", "AVS_BROWSER_PROFILE_DIR is not configured")
            return MediaResult(False, error=error, message=error.code, started_at=started, ended_at=_now())
        script = Path(__file__).resolve().parents[4] / "scripts" / "browser_profile_media_capture.mjs"
        command = ["node", str(script), "--url", video_url, "--video-id", video_id,
                   "--out-dir", str(out_dir), "--segment-seconds", str(self.segment_seconds)]
        for attempt in range(2):
            try:
                raw = self.runner(command)
            except subprocess.TimeoutExpired as exc:
                error = self._error("BROWSER_CAPTURE_TIMEOUT", str(exc))
                return MediaResult(False, error=error, message=str(exc)[:500], started_at=started, ended_at=_now())
            except OSError as exc:
                error = self._error("BROWSER_RUNTIME_UNAVAILABLE", str(exc))
                return MediaResult(False, error=error, message=str(exc)[:500], started_at=started, ended_at=_now())
            code = getattr(raw, "returncode", 0)
            stdout = str(getattr(raw, "stdout", "") or "").strip()
            stderr = str(getattr(raw, "stderr", "") or "").strip()
            payload: dict[str, object] = {}
            if stdout:
                try:
                    payload = json.loads(stdout.splitlines()[-1])
                except json.JSONDecodeError:
                    payload = {}
            if not code and payload.get("ok") and payload.get("path"):
                path = Path(str(payload["path"]))
                if path.is_file() and path.stat().st_size > 4096:
                    return MediaResult(True, path=path, message=json.dumps({k: v for k, v in payload.items() if k != "path"}, ensure_ascii=False),
                                       started_at=started, ended_at=_now())
            error_code = str(payload.get("error_code") or "BROWSER_CAPTURE_FAILED")
            error = self._error(error_code, stderr or stdout)
            if attempt == 0 and error.retryable:
                time.sleep(5)
                continue
            return MediaResult(False, error=error, message=(stderr or stdout or error_code)[:500],
                               return_code=code, started_at=started, ended_at=_now())
        raise AssertionError("browser capture retry loop exhausted")
