"""Secret masking: replace known secret values with ``***`` in a string."""

from __future__ import annotations

from collections.abc import Iterable

_MASK = "***"


def mask(text: str, secrets: Iterable[str]) -> str:
    """Replace every occurrence of each secret in ``text`` with ``***``.

    Secrets are applied longest-first so that a shorter secret never partially
    replaces a longer one (e.g. ``"abc"`` clobbering ``"abc123"``). Empty
    secrets are ignored.
    """
    result = text
    ordered = sorted({secret for secret in secrets if secret}, key=len, reverse=True)
    for secret in ordered:
        result = result.replace(secret, _MASK)
    return result
