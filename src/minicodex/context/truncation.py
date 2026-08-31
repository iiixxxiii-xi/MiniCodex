"""Observation truncation.

Long tool outputs are truncated to a hard length budget and annotated with a
notice that reports how many characters were dropped, so the model never
silently reasons over a quietly-clipped result.
"""

from __future__ import annotations

TRUNCATION_NOTICE = "\n...[output truncated: {omitted} characters omitted]"


def truncate_observation(text: str, max_len: int) -> str:
    """Truncate ``text`` to ``max_len`` characters, appending a notice when cut.

    Text at or under ``max_len`` is returned unchanged. When truncated, the
    returned string is the first ``max_len`` characters plus a notice reporting
    the number of omitted characters.

    Raises:
        ValueError: if ``max_len`` is negative.
    """
    if max_len < 0:
        raise ValueError("max_len must be non-negative")
    if len(text) <= max_len:
        return text
    omitted = len(text) - max_len
    return text[:max_len] + TRUNCATION_NOTICE.format(omitted=omitted)
