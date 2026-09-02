"""``LocalRuntime``: run tools directly on the host filesystem (no isolation).

Intended for tests and fast development only. Shell commands execute via
``subprocess`` and file operations use ``pathlib``; there is no sandboxing.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path

from minicodex.registry.registry import ToolRegistry
from minicodex.registry.schema import Tool
from minicodex.runtime.tools.common import ToolError, classify_error, failure

logger = logging.getLogger(__name__)


class LocalRuntime:
    """A ``Runtime`` that dispatches tool calls to local Python callables.

    Each tool is registered with both its declarative ``Tool`` (for schema
    output) and its callable. ``execute`` never raises: unknown tools, invalid
    arguments, and tool exceptions all become structured result dicts.
    """

    def __init__(self, cwd: str | Path | None = None) -> None:
        self.cwd = Path(cwd).resolve() if cwd else Path.cwd()
        self._registry = ToolRegistry()
        self._tools: dict[str, Callable] = {}
        self._started = False

    @property
    def started(self) -> bool:
        return self._started

    def register(self, tool_def: Tool, fn: Callable) -> None:
        self._registry.register(tool_def)
        self._tools[tool_def.name] = fn
        logger.debug("registered tool '%s'", tool_def.name)

    def schemas(self) -> list[dict]:
        return self._registry.schemas()

    async def execute(self, action: dict) -> dict:
        name = action.get("name")
        arguments = action.get("arguments", {})
        fn = self._tools.get(name)
        if fn is None:
            logger.warning("unknown tool '%s'", name)
            return failure(f"Unknown tool '{name}'", retryable=False)
        try:
            # Tools run subprocess/file IO synchronously; offload to a worker
            # thread so a blocking tool never stalls the event loop (and thus
            # other concurrently-running eval tasks).
            return await asyncio.to_thread(fn, arguments, cwd=self.cwd)
        except ToolError as exc:
            return failure(exc.message, retryable=exc.retryable)
        except Exception as exc:  # pragma: no cover - defensive last resort
            logger.exception("tool '%s' raised", name)
            return failure(f"Tool '{name}' failed: {exc}", retryable=classify_error(exc))

    def register_builtins(self) -> None:
        from minicodex.runtime.tools import BUILTIN_TOOLS

        for tool_def, fn in BUILTIN_TOOLS:
            self.register(tool_def, fn)

    def start(self) -> None:
        self._started = True
        logger.info("local runtime started (cwd=%s)", self.cwd)

    def stop(self) -> None:
        self._started = False
        logger.info("local runtime stopped")


def builtin_runtime(cwd: str | Path | None = None) -> LocalRuntime:
    """A ``LocalRuntime`` preloaded with the built-in tool set."""
    runtime = LocalRuntime(cwd=cwd)
    runtime.register_builtins()
    return runtime
