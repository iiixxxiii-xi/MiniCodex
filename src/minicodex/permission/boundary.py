"""Workspace boundary enforcement.

``is_within_workspace`` decides whether a (possibly relative, possibly
symlinked) path resolves to a location inside a workspace root, rejecting
``..`` traversal and absolute-path escapes.
"""

from __future__ import annotations

from pathlib import Path


def is_within_workspace(path: str | Path, root: str | Path) -> bool:
    """Return True when ``path`` resolves to a location within ``root``.

    Relative paths are resolved against ``root``; absolute paths are resolved
    as-is. Both ``..`` traversal and symlinks are resolved before the check, so
    escapes are detected regardless of how they are spelled.
    """
    root_path = Path(root).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root_path / candidate
    try:
        resolved = candidate.resolve()
    except (OSError, RuntimeError):  # symlink loop or unresolvable path
        return False
    return resolved.is_relative_to(root_path)
