"""M2 transcript extraction orchestration: captions first, Whisper fallback, QA and resume."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from .asr import FasterWhisperProvider
from .captions import YtDlpCaptionProvider
from .media import BrowserProfileMediaProvider, YtDlpMediaProvider
from .storage import load_catalog, update_video_state
from .transcript import canonical_from_captions, canonical_from_whisper, write_canonical, write_transcript_markdown
from .transcript_quality import TranscriptQA, assess_transcript


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_attempt(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def _find_video(root: Path, video_id: str) -> dict[str, Any]:
    for row in load_catalog(root):
        if row.get("video_id") == video_id:
            return row
    raise KeyError(f"video_id not found in catalog: {video_id}")


def _failure_status(error: Any) -> str:
    if error is None:
        return "UNAVAILABLE"
    # A provider challenge is not a video-level terminal state.  It remains
    # eligible for the browser-profile fallback and, if that also fails, for a
    # later retry sweep.
    if getattr(error, "blocked", False) or getattr(error, "retryable", False):
        return "RETRYABLE_FAILED"
    code = str(getattr(error, "code", "UNAVAILABLE"))
    return code if code in {"PRIVATE", "DELETED", "UNAVAILABLE"} else "UNAVAILABLE"


def _write_qa(path: Path, qa: TranscriptQA, *, forced_asr: bool = False) -> None:
    payload = qa.to_dict()
    payload["forced_asr"] = forced_asr
    _safe_json(path, payload)


def _validate_output_schemas(transcript: Any, qa: dict[str, Any]) -> None:
    schema_root = Path(__file__).resolve().parents[4] / "schemas"
    jsonschema.validate(transcript.to_dict(), json.loads((schema_root / "research-transcript.schema.json").read_text(encoding="utf-8")))
    jsonschema.validate(qa, json.loads((schema_root / "research-transcript-qa.schema.json").read_text(encoding="utf-8")))


def extract_transcript(root: Path, video_id: str, *, force: bool = False, force_asr: bool = False,
                       model: str = "small", language: str | None = "zh", device: str = "auto",
                       keep_media: bool = False, caption_provider: YtDlpCaptionProvider | None = None,
                       media_provider: YtDlpMediaProvider | None = None,
                       browser_media_provider: BrowserProfileMediaProvider | None = None,
                       asr_provider: FasterWhisperProvider | None = None) -> dict[str, Any]:
    row = _find_video(root, video_id)
    video_root = root / "videos" / video_id
    transcript_root = video_root / "transcript"
    raw_root = transcript_root / "raw"
    media_root = video_root / "media"
    canonical_path = transcript_root / "canonical.json"
    qa_path = transcript_root / "qa.json"
    attempts_path = video_root / "attempts.jsonl"
    if not force and canonical_path.exists() and qa_path.exists():
        try:
            prior = json.loads(qa_path.read_text(encoding="utf-8"))
            if prior.get("status") == "PASS":
                return {"video_id": video_id, "status": "SKIPPED", "reason": "QA_PASSED", "source_type":
                        json.loads(canonical_path.read_text(encoding="utf-8")).get("source_type")}
        except (OSError, json.JSONDecodeError):
            pass
    video_root.mkdir(parents=True, exist_ok=True)
    metadata = dict(row)
    metadata.pop("attempts", None)
    _safe_json(video_root / "metadata.json", metadata)
    attempts: list[dict[str, Any]] = []
    transcript = None
    qa: TranscriptQA | None = None
    selected_source: str | None = None
    forced_provenance = {"forced_asr": bool(force_asr), "catalog_url": row.get("url"), "video_id": video_id}

    if not force_asr:
        update_video_state(root, video_id, extraction_status="CAPTION_PENDING")
        captions = (caption_provider or YtDlpCaptionProvider()).fetch(row["url"], video_id, raw_root)
        for item in captions.attempts or []:
            attempts.append(item)
            _append_attempt(attempts_path, item)
        if captions.ok and captions.segments:
            selected_source = captions.source_type
            raw_path = None
            if captions.path is not None:
                try:
                    raw_path = str(captions.path.relative_to(video_root))
                except ValueError:
                    raw_path = str(captions.path)
            transcript = canonical_from_captions(video_id, language=captions.language or "unknown",
                                                 source_type=captions.source_type or "MANUAL_CAPTION",
                                                 provider="yt-dlp", segments=captions.segments,
                                                 provenance={**forced_provenance, "raw_path": raw_path})
            qa = assess_transcript(transcript, duration=row.get("duration"))
            _write_qa(qa_path, qa, forced_asr=False)
            if qa.status in {"PASS", "WARN"}:
                update_video_state(root, video_id, extraction_status="TRANSCRIPT_QA_PASSED")
            else:
                update_video_state(root, video_id, extraction_status="CAPTION_UNAVAILABLE")
        else:
            update_video_state(root, video_id, extraction_status="CAPTION_UNAVAILABLE")
            if captions.error and not captions.attempts:
                attempts.append({"provider": "yt-dlp-caption", "result": captions.error.code,
                                 "message": captions.message, "started_at": captions.started_at,
                                 "ended_at": captions.ended_at})
                _append_attempt(attempts_path, attempts[-1])

    if transcript is None or (qa is not None and qa.status == "FAIL"):
        update_video_state(root, video_id, extraction_status="MEDIA_PENDING")
        media = (media_provider or YtDlpMediaProvider()).download(row["url"], video_id, media_root)
        media_attempt = {"provider": "yt-dlp-media", "result": "MEDIA_OK" if media.ok else (media.error.code if media.error else "UNAVAILABLE"),
                         "message": media.message, "started_at": media.started_at, "ended_at": media.ended_at,
                         "return_code": media.return_code}
        attempts.append(media_attempt)
        _append_attempt(attempts_path, media_attempt)
        if not media.ok or media.path is None:
            # YouTube challenge/403/PO-token failures are acquisition failures;
            # give the already-verified browser profile path one chance before
            # classifying the video itself as unavailable.
            blocked_or_retryable = bool(media.error and (media.error.blocked or media.error.retryable))
            truly_terminal = bool(media.error and media.error.code in {"PRIVATE", "DELETED"})
            if not truly_terminal and (blocked_or_retryable or media.error is None or media.error.code not in {"PRIVATE", "DELETED"}):
                browser_provider = browser_media_provider or BrowserProfileMediaProvider()
                if isinstance(browser_provider, BrowserProfileMediaProvider):
                    browser_provider.timeout = browser_provider.timeout_for_duration(row.get("duration"))
                browser = browser_provider.download(row["url"], video_id, media_root)
                browser_attempt = {"provider": "browser-profile-media-capture",
                                   "result": "MEDIA_OK" if browser.ok else (browser.error.code if browser.error else "UNAVAILABLE"),
                                   "message": browser.message, "started_at": browser.started_at, "ended_at": browser.ended_at,
                                   "return_code": browser.return_code}
                attempts.append(browser_attempt)
                _append_attempt(attempts_path, browser_attempt)
                # Classification must use the last provider actually tried;
                # otherwise a browser PRIVATE/timeout is masked by yt-dlp's
                # earlier challenge error.
                media = browser
                if browser.ok and browser.path is not None:
                    media = browser
            if not media.ok or media.path is None:
                status = _failure_status(media.error)
                update_video_state(root, video_id, extraction_status=status, attempts=attempts)
                return {"video_id": video_id, "status": status, "attempts": attempts}
        update_video_state(root, video_id, extraction_status="MEDIA_OK", attempts=attempts)
        update_video_state(root, video_id, extraction_status="ASR_PENDING", attempts=attempts)
        asr = (asr_provider or FasterWhisperProvider(model_size=model, language=language, device=device)).transcribe(
            media.path, video_id=video_id, provenance=forced_provenance)
        asr_attempt = {"provider": "faster-whisper", "result": "ASR_OK" if asr.ok else "UNAVAILABLE",
                        "message": asr.message, "started_at": _now(), "ended_at": _now()}
        attempts.append(asr_attempt)
        _append_attempt(attempts_path, asr_attempt)
        if not asr.ok or asr.payload is None:
            update_video_state(root, video_id, extraction_status="UNAVAILABLE", attempts=attempts)
            return {"video_id": video_id, "status": "UNAVAILABLE", "attempts": attempts}
        transcript = canonical_from_whisper(video_id, asr.payload, provenance=forced_provenance)
        selected_source = transcript.source_type
        qa = assess_transcript(transcript, duration=row.get("duration"))
        _write_qa(qa_path, qa, forced_asr=force_asr)
        update_video_state(root, video_id, extraction_status="ASR_OK", attempts=attempts)

    if transcript is None or qa is None:
        raise RuntimeError("transcript pipeline produced no result")
    _validate_output_schemas(transcript, {**qa.to_dict(), "forced_asr": force_asr})
    write_canonical(canonical_path, transcript)
    write_transcript_markdown(transcript_root / "transcript.md", transcript)
    if qa.status in {"PASS", "WARN"}:
        update_video_state(root, video_id, extraction_status="TRANSCRIPT_QA_PASSED", attempts=attempts)
    else:
        update_video_state(root, video_id, extraction_status="UNAVAILABLE", attempts=attempts)
    if not keep_media and media_root.exists():
        for path in media_root.iterdir():
            if path.is_file():
                path.unlink()
        try:
            media_root.rmdir()
        except OSError:
            pass
    return {"video_id": video_id, "status": "PASS" if qa.status in {"PASS", "WARN"} else "FAIL",
            "source_type": selected_source, "qa": qa.to_dict(), "attempts": attempts,
            "forced_asr": force_asr}
