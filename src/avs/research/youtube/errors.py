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
    if "private video" in text or "private" in text:
        return ClassifiedError("PRIVATE", False)
    if "deleted video" in text or "video unavailable" in text and "deleted" in text:
        return ClassifiedError("DELETED", False)
    if "age-restricted" in text or "age restricted" in text:
        return ClassifiedError("AGE_RESTRICTED", False)
    if "sign in to confirm" in text or "not a bot" in text:
        return ClassifiedError("SIGN_IN_CONFIRM_BOT", False, True)
    if "ip blocked" in text or "too many requests" in text:
        return ClassifiedError("IP_BLOCKED", False, True)
    if "po token" in text or "pot required" in text:
        return ClassifiedError("PO_TOKEN_REQUIRED", False, True)
    if "403" in text or "forbidden" in text or exit_code == 403:
        return ClassifiedError("HTTP_403", False, True)
    if "timeout" in text or "timed out" in text or "temporarily unavailable" in text:
        return ClassifiedError("NETWORK_TIMEOUT", True)
    if "caption" in text and ("unavailable" in text or "not found" in text):
        return ClassifiedError("CAPTION_UNAVAILABLE", False)
    if "unavailable" in text:
        return ClassifiedError("UNAVAILABLE", False)
    return ClassifiedError("FAILED_UNKNOWN", False)

