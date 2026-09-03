"""Word wrapping and substring search."""

from textutils._helpers import split_words


def wrap(text: str, width: int) -> str:
    """Wrap ``text`` into lines of at most ``width`` characters without breaking
    words. Lines are joined with newlines.

    Words longer than ``width`` are left unbroken on their own line.
    """
    words = split_words(text)
    if not words:
        return ""
    lines = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= width:
            current += " " + word
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return "\n".join(lines)


def count_occurrences(text: str, sub: str) -> int:
    """Count non-overlapping occurrences of ``sub`` in ``text``.

    ``count_occurrences("aaaa", "aa")`` -> 2 (non-overlapping). An empty ``sub``
    returns 0.
    """
    if not sub:
        return 0
    count = 0
    start = 0
    while True:
        idx = text.find(sub, start)
        if idx == -1:
            return count
        count += 1
        start = idx + len(sub)
