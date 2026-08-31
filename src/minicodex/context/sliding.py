"""Sliding-window context trimming.

Keeps only the most recent ``n`` non-system messages, while always preserving
system messages (they carry the agent's fixed instructions and must never slide
out of the window).
"""

from __future__ import annotations


def slide(messages: list[dict], n: int) -> list[dict]:
    """Return ``messages`` trimmed to the last ``n`` non-system messages.

    System messages (``role == "system"``) are always preserved, in their
    original relative order, ahead of the retained non-system messages.

    A non-positive ``n`` keeps only the system messages. When there are fewer
    than ``n`` non-system messages, all of them are kept.
    """
    if n < 0:
        n = 0
    system = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]
    if n == 0:
        return system
    return system + non_system[-n:]
