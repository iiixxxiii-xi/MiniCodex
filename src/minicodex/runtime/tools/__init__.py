"""Built-in runtime tools and their declarative definitions.

``BUILTIN_TOOLS`` pairs each tool's ``Tool`` schema with its callable, so a
``LocalRuntime`` can register the full tool set and expose function schemas to a
model.
"""

from __future__ import annotations

from collections.abc import Callable

from minicodex.registry.schema import Tool
from minicodex.runtime.tools import (
    apply_patch,
    git,
    grep,
    read_file,
    shell,
    test_runner,
    write_file,
)

BUILTIN_TOOLS: list[tuple[Tool, Callable]] = [
    (read_file.TOOL, read_file.run),
    (write_file.TOOL, write_file.run),
    (grep.TOOL, grep.run),
    (apply_patch.TOOL, apply_patch.run),
    (shell.TOOL, shell.run),
    (git.TOOL, git.run),
    (test_runner.TOOL, test_runner.run),
]

__all__ = ["BUILTIN_TOOLS"]
