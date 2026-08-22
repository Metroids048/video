"""yt-dlp caption acquisition with manual/automatic separation and bounded calls."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .errors import ClassifiedError, classify_error
from .transcript import parse_vtt


LANGUAGE_PRIORITY = ("zh-Hans", "zh-Hant", "zh", "zh-CN", "zh-TW", "zh-HK", "en")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class CaptionResult:
    ok: bool
    source_type: str | None = None
    language: str | None = None
    path: Path | None = None
    segments: list | None = None
    error: ClassifiedError | None = None
    message: str = ""
    return_code: int | None = None
    started_at: str = ""
    ended_at: str = ""
    attempts: list[dict] | None = None


class YtDlpCaptionProvider:
    name = "yt-dlp-caption"

    def __init__(self, *, runner: Callable[[list[str]], subprocess.CompletedProcess | object] | None = None,
                 timeout: int = 120, max_retries: int = 1):
        self.runner = runner or self._run
        self.timeout = timeout
        self.max_retries = max(0, min(max_retries, 1))

    def _run(self, command: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(command, capture_output=True, text=True, timeout=self.timeout, shell=False)

    @staticmethod
    def _select_artifact(directory: Path, video_id: str, languages: tuple[str, ...]) -> tuple[Path | None, str | None]:
        candidates = sorted(directory.glob(f"{video_id}*.vtt"))
        if not candidates:
            return None, None
        def score(path: Path) -> tuple[int, str]:
            name = path.name.lower()
            for index, language in enumerate(languages):
                if language.lower() in name:
                    return index, name
            return len(languages) + 1, name
        chosen = sorted(candidates, key=score)[0]
        language = None
        for item in languages:
            if item.lower() in chosen.name.lower():
                language = item
                break
        return chosen, language or "unknown"

    def _attempt(self, video_url: str, video_id: str, out_dir: Path, *, generated: bool) -> CaptionResult:
        out_dir.mkdir(parents=True, exist_ok=True)
        started = _now()
        before = set(out_dir.glob(f"{video_id}*.vtt"))
        mode_flag = "--write-auto-subs" if generated else "--write-subs"
        command = ["yt-dlp", "--skip-download", "--no-playlist", "--no-warnings", mode_flag,
                   "--sub-format", "vtt", "--sub-langs", ",".join(LANGUAGE_PRIORITY),
                   "-o", str(out_dir / f"{video_id}.%(ext)s"), video_url]
        try:
            raw = self.runner(command)
            code = getattr(raw, "returncode", 0)
            stdout = str(getattr(raw, "stdout", "") or "")
            stderr = str(getattr(raw, "stderr", "") or "")
            if code:
                classified = classify_error(stderr or stdout, exit_code=code)
                return CaptionResult(False, error=classified, message=(stderr or stdout).strip()[:500],
                                     return_code=code, started_at=started, ended_at=_now())
        except subprocess.TimeoutExpired as exc:
            return CaptionResult(False, error=ClassifiedError("NETWORK_TIMEOUT", True), message=str(exc),
                                 started_at=started, ended_at=_now())
        except OSError as exc:
            return CaptionResult(False, error=classify_error(str(exc)), message=str(exc), started_at=started, ended_at=_now())
        path, language = self._select_artifact(out_dir, video_id, LANGUAGE_PRIORITY)
        if path is None:
            # Some test runners write a differently named file; only accept new VTT files.
            new_files = sorted(set(out_dir.glob("*.vtt")) - before)
            path = new_files[0] if new_files else None
        if path is None:
            return CaptionResult(False, error=ClassifiedError("CAPTION_UNAVAILABLE", False),
                                 message="no requested caption artifact", started_at=started, ended_at=_now())
        try:
            embedded_language, segments = parse_vtt(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            return CaptionResult(False, error=ClassifiedError("CAPTION_UNAVAILABLE", False), message=str(exc),
                                 started_at=started, ended_at=_now())
        return CaptionResult(True, "AUTO_CAPTION" if generated else "MANUAL_CAPTION", embedded_language or language,
                             path, segments, started_at=started, ended_at=_now())

    def fetch(self, video_url: str, video_id: str, out_dir: Path) -> CaptionResult:
        manual = self._attempt(video_url, video_id, out_dir, generated=False)
        if manual.error and manual.error.retryable and self.max_retries:
            retry = self._attempt(video_url, video_id, out_dir, generated=False)
            manual = retry
        if manual.ok:
            manual.attempts = [{"provider": self.name, "mode": "manual", "result": "CAPTION_OK",
                                "started_at": manual.started_at, "ended_at": manual.ended_at}]
            return manual
        auto = self._attempt(video_url, video_id, out_dir, generated=True)
        if auto.error and auto.error.retryable and self.max_retries:
            auto = self._attempt(video_url, video_id, out_dir, generated=True)
        if auto.ok:
            auto.attempts = [self._attempt_dict(manual, "manual"), {"provider": self.name, "mode": "auto",
                            "result": "CAPTION_OK", "started_at": auto.started_at, "ended_at": auto.ended_at}]
            return auto
        # Preserve the most actionable deterministic failure from the auto attempt.
        selected = auto if auto.error and auto.error.code not in {"CAPTION_UNAVAILABLE", "CAPTION_DISABLED", "NO_REQUESTED_LANGUAGE"} else manual
        selected.attempts = [self._attempt_dict(manual, "manual"), self._attempt_dict(auto, "auto")]
        return selected

    @staticmethod
    def _attempt_dict(result: CaptionResult, mode: str) -> dict:
        return {"provider": "yt-dlp-caption", "mode": mode,
                "result": result.error.code if result.error else ("CAPTION_OK" if result.ok else "FAILED"),
                "started_at": result.started_at, "ended_at": result.ended_at,
                "return_code": result.return_code, "message": result.message[:500]}
