"""Retry with exponential backoff and error classification for model calls."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Exception class-name substrings that indicate a transient, retryable failure.
_RETRYABLE_NAME_TOKENS = ("Timeout", "Connection", "RateLimit")


def is_retryable(exc: Exception) -> bool:
    """Return True if ``exc`` is a transient failure worth retrying.

    HTTP status 429 and 5xx are retryable; other 4xx are not. Timeout /
    connection / rate-limit errors are retryable by class name.
    """
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status == 429 or status >= 500
    name = type(exc).__qualname__
    return any(token in name for token in _RETRYABLE_NAME_TOKENS)


def with_retry(
    fn: Callable[[], T],
    *,
    retry_on: Callable[[Exception], bool] = is_retryable,
    max_attempts: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    log: logging.Logger = logger,
) -> T:
    """Call ``fn``, retrying retryable failures with exponential backoff.

    Non-retryable failures propagate immediately. Retryable failures are retried
    up to ``max_attempts`` total attempts; on exhaustion the last exception is
    re-raised.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            return fn()
        except Exception as exc:
            retryable = retry_on(exc)
            if not retryable or attempt >= max_attempts:
                log.error("model call failed after %d attempt(s): %s", attempt, exc)
                raise
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            log.warning(
                "retryable model error (attempt %d/%d): %s; retrying in %.1fs",
                attempt,
                max_attempts,
                exc,
                delay,
            )
            time.sleep(delay)
