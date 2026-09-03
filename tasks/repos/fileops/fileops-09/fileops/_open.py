"""Shared file-opening and path helpers (private)."""

from contextlib import contextmanager
from pathlib import Path


@contextmanager
def open_text(path, mode="r", encoding="utf-8", newline=None):
    """Open ``path`` as a text file and yield the handle, closing it on exit."""
    handle = open(path, mode, encoding=encoding, newline=newline)
    yield handle


def ensure_parent(path):
    """Create the parent directory of ``path`` (if any) and return ``path``."""
    parent = Path(path).parent
    if str(parent) not in ("", "."):
        parent.mkdir(parents=True, exist_ok=True)
    return str(path)
