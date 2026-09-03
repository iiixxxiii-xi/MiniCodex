"""Reading text files: whole-file lines, tails, and line counts."""

from fileops._open import open_text


def read_lines(path):
    """Return the lines of ``path`` as strings, with trailing newlines stripped."""
    with open_text(path, "r") as handle:
        return [line.rstrip() for line in handle]


def tail(path, n):
    """Return the last ``n`` lines of ``path`` (trailing newlines stripped)."""
    with open_text(path, "r") as handle:
        lines = [line.rstrip("\n") for line in handle]
    return lines[-n:]


def count_lines(path):
    """Return the number of lines in ``path`` (0 for an empty file)."""
    with open_text(path, "r") as handle:
        return sum(1 for _ in handle)
