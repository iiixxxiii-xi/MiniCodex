"""Line-oriented text helpers and ``key=value`` parsing."""


def strip_comments(line: str) -> str:
    """Remove an inline comment (everything from the first ``#`` or ``;``).

    Returns the line with trailing whitespace stripped. A line with no comment
    marker is returned with only its trailing whitespace stripped.
    """
    positions = [line.find(marker) for marker in ("#", ";")]
    positions = [p for p in positions if p != -1]
    if not positions:
        return line.rstrip()
    return line[:min(positions)].rstrip()


def split_words(text: str) -> list[str]:
    """Split ``text`` into words on runs of whitespace.

    ``"a  b"`` -> ``["a", "b"]``; never emits empty tokens for leading,
    trailing, or repeated whitespace.
    """
    return text.split()


def parse_kv(line: str, sep: str = "=") -> tuple[str, str] | None:
    """Parse one ``key sep value`` line into a ``(key, value)`` tuple.

    Leading/trailing whitespace and inline comments are ignored. Blank or
    comment-only lines return ``None``. Only the first ``sep`` splits, so the
    value may itself contain the separator (``"url=a=b"`` -> ``("url", "a=b")``).
    A line containing neither ``sep`` nor a value raises ``ValueError``.
    """
    cleaned = strip_comments(line).strip()
    if not cleaned:
        return None
    if sep not in cleaned:
        raise ValueError(f"line has no '{sep}' separator: {line!r}")
    key, value = cleaned.split(sep)
    return key.strip(), value.strip()
