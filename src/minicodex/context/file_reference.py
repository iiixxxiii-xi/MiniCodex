"""File-reference offload.

Large inline content (tool outputs, file dumps) is written to disk and replaced
in the conversation by a short path reference, keeping the token budget low while
preserving the full content on disk for later inspection.
"""

from __future__ import annotations

from pathlib import Path


def offload(content: str, path: str | Path) -> str:
    """Write ``content`` to ``path`` and return a reference string.

    Parent directories are created as needed.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"[content offloaded to {path}]"


def replace_if_large(text: str, path: str | Path, max_len: int) -> str:
    """Return ``text`` unchanged unless it exceeds ``max_len`` characters.

    Oversized text is offloaded to ``path`` and replaced by a path reference.
    """
    if len(text) <= max_len:
        return text
    return offload(text, path)
