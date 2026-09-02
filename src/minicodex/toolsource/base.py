"""Tool-source abstraction: a pluggable provider of tools for the agent loop.

The controller loop stays thin: it does not know whether a tool is implemented
in-process (built-in) or served by an external MCP server. Anything that satisfies
the :class:`ToolSource` protocol is an interchangeable provider of tool schemas
and tool executions.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ToolSource(Protocol):
    """A source of tools the agent can call.

    Two methods define the contract:

    * ``schemas()`` returns the function-calling schemas shown to the model.
    * ``call(name, arguments)`` invokes one tool and returns a structured result
      dict (``{"output", "returncode", "error", ...}``) — never raises.
    """

    def schemas(self) -> list[dict]: ...

    def call(self, name: str, arguments: dict) -> dict: ...


class ToolSourceError(Exception):
    """Base error for tool-source failures."""


class DuplicateToolError(ToolSourceError):
    """Two sources declared a tool under the same name."""


def source_failure(error: str, *, retryable: bool = False, output: str = "") -> dict:
    """Build a structured failure result, mirroring the built-in tool result shape."""
    return {"output": output, "returncode": 1, "error": error, "retryable": retryable}
