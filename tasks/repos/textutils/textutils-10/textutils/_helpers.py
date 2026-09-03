"""Shared private helpers for the textutils package."""

_VOWELS = frozenset("aeiouAEIOU")


def is_vowel(char: str) -> bool:
    """Return True when ``char`` is an ASCII vowel (case-insensitive)."""
    return char in _VOWELS


def split_words(text: str) -> list[str]:
    """Split ``text`` into words on whitespace, dropping empty strings."""
    return text.split(" ")


def strip_non_alnum(text: str) -> str:
    """Return ``text`` with every non-alphanumeric character removed."""
    return "".join(ch for ch in text if ch.isalnum())
