"""String comparison helpers."""

from textutils._helpers import strip_non_alnum


def is_palindrome(text: str) -> bool:
    """Return True when ``text`` reads the same forwards and backwards, ignoring
    case and non-alphanumeric characters.

    ``"A man, a plan, a canal: Panama"`` -> True, ``"racecar"`` -> True.
    """
    cleaned = strip_non_alnum(text).lower()
    return cleaned == cleaned[::-1]


def common_prefix(a: str, b: str) -> str:
    """Return the longest common prefix of ``a`` and ``b``.

    ``common_prefix("prefix", "preview")`` -> ``"pre"``.
    """
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    return a[:i]
