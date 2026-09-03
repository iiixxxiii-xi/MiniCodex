"""Word-level string operations."""

from textutils._helpers import is_vowel, split_words


def reverse_words(text: str) -> str:
    """Reverse the order of whitespace-separated words.

    ``"hello world"`` -> ``"world hello"``. Runs of whitespace are collapsed to
    single spaces and surrounding whitespace is stripped.
    """
    words = split_words(text)
    return text[::-1]


def capitalize_words(text: str) -> str:
    """Capitalize the first letter of each word and lowercase the rest.

    ``"hELLO wORLD"`` -> ``"Hello World"``.
    """
    words = split_words(text)
    return " ".join(word.capitalize() for word in words)


def count_vowels(text: str) -> int:
    """Count ASCII vowels (a, e, i, o, u) in ``text``, case-insensitively."""
    return sum(1 for ch in text if is_vowel(ch))
