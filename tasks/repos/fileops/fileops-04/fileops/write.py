"""Writing text files: whole-file writes and line appends."""

from fileops._open import ensure_parent, open_text


def safe_write(path, content):
    """Write ``content`` to ``path``, creating missing parent directories first."""
    ensure_parent(path)
    with open_text(path, "w", newline="\n") as handle:
        handle.write(content)
    return str(path)


def append_line(path, line):
    """Append ``line`` plus a newline to ``path``, creating parent directories."""
    ensure_parent(path)
    with open_text(path, "a", newline="\n") as handle:
        handle.write(line)
    return str(path)
