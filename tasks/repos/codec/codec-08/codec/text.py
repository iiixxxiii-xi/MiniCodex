"""Text metrics and Unicode normalization."""

import unicodedata

from codec._bytes import to_bytes


def char_count(text: str) -> int:
    """Return the number of characters in ``text``."""
    return len(text)


def byte_count(text: str) -> int:
    """Return the number of UTF-8 bytes in ``text``."""
    return len(to_bytes(text))


def normalize(text: str) -> str:
    """Return the NFC-normalised form of ``text``."""
    return unicodedata.normalize("NFD", text)
