"""Classify deterministic YouTube/provider failures without unbounded retries."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassifiedError:
    code: str
    retryable: bool
    blocked: bool = False


def classify_error(message: str, *, exit_code: int | None = None) -> ClassifiedError:
    text = (message or "").lower()
    if "po token" in text or "pot required" in text or "proof of origin" in text:
        return ClassifiedError("PO_TOKEN_REQUIRED", False, True)
    if "sign in to confirm" in text or "not a bot" in text or "confirm you're not" in text:
        return ClassifiedError("SIGN_IN_CONFIRM_BOT", False, True)
    if "ip blocked" in text or "ipblock" in text or "too many requests" in text:
        return ClassifiedError("IP_BLOCKED", False, True)
    if "request blocked" in text or "requestblock" in text:
        return ClassifiedError("REQUEST_BLOCKED", False, True)
    if "429" in text or "rate limit" in text:
        return ClassifiedError("HTTP_429", False, True)
    if "private video" in text or "private" in text:
        return ClassifiedError("PRIVATE", False)
    if "deleted video" in text or "video has been removed" in text or ("video unavailable" in text and "deleted" in text):
        return ClassifiedError("DELETED", False)
    if "age-restricted" in text or "age restricted" in text:
        return ClassifiedError("AGE_RESTRICTED", False)
    if "403" in text or "forbidden" in text or exit_code == 403:
        return ClassifiedError("HTTP_403", False, True)
    if "timeout" in text or "timed out" in text or "temporarily unavailable" in text:
        return ClassifiedError("NETWORK_TIMEOUT", True)
    if "caption" in text and ("disabled" in text or "turned off" in text):
        return ClassifiedError("CAPTION_DISABLED", False)
    if "no requested" in text or "requested language" in text:
        return ClassifiedError("NO_REQUESTED_LANGUAGE", False)
    if "caption" in text and ("unavailable" in text or "not found" in text or "no subtitles" in text):
        return ClassifiedError("CAPTION_UNAVAILABLE", False)
    if "format" in text and "available" in text:
        return ClassifiedError("MEDIA_FORMAT_UNAVAILABLE", False)
    if "unavailable" in text:
        return ClassifiedError("UNAVAILABLE", False)
    if "network" in text or "connection" in text or "temporary failure" in text:
        return ClassifiedError("NETWORK_ERROR", True)
    return ClassifiedError("UNKNOWN_PROVIDER_ERROR", False)
