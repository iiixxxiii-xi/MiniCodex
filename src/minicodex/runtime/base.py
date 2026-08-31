"""Runtime protocol: the execution environment an agent drives with tool calls."""

from __future__ import annotations

from typing import Protocol


class Runtime(Protocol):
    """A sandbox/executor that turns tool actions into observations.

    An ``action`` is ``{"name": str, "arguments": dict}``. ``execute`` returns a
    structured observation dict that always carries ``output``, ``returncode``,
    ``error`` (empty on success) and, on failure, ``retryable`` — so a controller
    loop never receives an unhandled exception from a tool.
    """

    def execute(self, action: dict) -> dict: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...
