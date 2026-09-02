"""``McpToolSource``: expose an external MCP server's tools to the agent.

The MCP server is spoken to through a small synchronous client interface
(:class:`McpClient`); the default implementation bridges the async ``mcp`` SDK
client over a background event loop for both stdio and HTTP transports. The
client is injectable so ``McpToolSource`` itself is fully unit-testable without
a live server.

Every failure — connection refused, server dropped, tool raised, or an
unexpected SDK error — is degraded to a structured result dict (never an
unhandled exception). When the server cannot be reached the source simply
contributes no schemas, so the agent runs without the external tools.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import shlex
import sys
import threading
from contextlib import AsyncExitStack
from typing import Protocol

from minicodex.toolsource.base import source_failure

logger = logging.getLogger(__name__)


class McpError(Exception):
    """Base error for MCP client failures."""


class McpConnectionError(McpError):
    """The MCP server could not be reached (or the connection was lost)."""


class McpCallError(McpError):
    """A tool call to the MCP server failed."""


class McpClient(Protocol):
    """Synchronous MCP client facade (injectable for tests).

    ``list_tools`` returns plain descriptors: ``{"name", "description",
    "input_schema"}``. ``call_tool`` returns ``{"output", "is_error"}``.
    """

    def list_tools(self) -> list[dict]: ...

    def call_tool(self, name: str, arguments: dict) -> dict: ...

    def close(self) -> None: ...


def _tool_to_schema(tool: dict) -> dict:
    """Convert an MCP tool descriptor into an OpenAI function-calling schema."""
    name = tool.get("name", "")
    description = tool.get("description") or ""
    parameters = tool.get("input_schema") or tool.get("parameters") or {}
    return {
        "type": "function",
        "function": {"name": name, "description": description, "parameters": parameters},
    }


class McpToolSource:
    """A :class:`ToolSource` backed by an external MCP server.

    Tool listing is lazy and cached. A connection failure leaves ``schemas()``
    empty (and ``call`` reporting a structured, retryable error), so the loop
    never sees an unhandled exception from the MCP layer.
    """

    def __init__(self, client: McpClient):
        self.client = client
        self._schemas: list[dict] | None = None
        self._tool_names: set[str] = set()
        self._connect_error: str | None = None

    def schemas(self) -> list[dict]:
        if self._schemas is None:
            try:
                tools = self.client.list_tools()
            except Exception as exc:  # noqa: BLE001 - degrade, never raise
                self._connect_error = _message(exc)
                logger.warning("MCP server unreachable: %s", self._connect_error)
                self._schemas = []
            else:
                self._schemas = [_tool_to_schema(tool) for tool in tools]
                self._tool_names = {tool.get("name", "") for tool in tools}
        return list(self._schemas)

    def call(self, name: str, arguments: dict) -> dict:
        if self._connect_error is not None:
            return source_failure(f"MCP server unavailable: {self._connect_error}", retryable=True)
        try:
            result = self.client.call_tool(name, arguments)
        except McpConnectionError as exc:
            return source_failure(f"MCP connection lost: {exc}", retryable=True)
        except McpCallError as exc:
            return source_failure(str(exc), retryable=False)
        except Exception as exc:  # noqa: BLE001 - defensive last resort
            return source_failure(f"MCP tool '{name}' failed: {exc}", retryable=False)
        if result.get("is_error"):
            return source_failure(
                result.get("output") or f"MCP tool '{name}' returned an error", retryable=False
            )
        return {"output": result.get("output", ""), "returncode": 0, "error": ""}

    def close(self) -> None:
        close = getattr(self.client, "close", None)
        if callable(close):
            try:
                close()
            except Exception:  # noqa: BLE001 - best-effort teardown
                logger.warning("failed to close MCP client", exc_info=True)


def _message(exc: BaseException) -> str:
    return str(exc) or type(exc).__name__


def _extract_text(result) -> str:
    """Flatten an MCP ``CallToolResult`` into a single text string."""
    parts: list[str] = []
    for block in result.content or []:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
        else:
            parts.append(repr(block))
    if not parts:
        structured = getattr(result, "structured_content", None)
        if structured is not None:
            try:
                return json.dumps(structured, ensure_ascii=False)
            except (TypeError, ValueError):
                return str(structured)
    return "\n".join(parts)


class _SessionMcpClient:
    """Synchronous facade over an async ``mcp`` ``ClientSession``.

    A dedicated event loop runs on a daemon thread; the session is established
    lazily on first use and shared across ``list_tools`` / ``call_tool``.
    Connection and call failures are raised as :class:`McpConnectionError` /
    :class:`McpCallError`.
    """

    def __init__(self, *, connect_timeout: float = 10.0, call_timeout: float = 60.0):
        self._connect_timeout = connect_timeout
        self._call_timeout = call_timeout
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._session = None
        self._ready: concurrent.futures.Future | None = None
        self._closed: asyncio.Event | None = None
        self._runner_future: concurrent.futures.Future | None = None

    # -- transport hook (subclass) ------------------------------------------

    def _transport_cm(self):
        """Return an async context manager yielding ``(read, write, ...)``."""
        raise NotImplementedError

    # -- lifecycle -----------------------------------------------------------

    def _ensure(self) -> None:
        if self._session is not None:
            return
        if sys.platform == "win32" and not isinstance(
            asyncio.get_event_loop_policy(), asyncio.WindowsSelectorEventLoopPolicy
        ):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True, name="mcp-client")
        self._thread.start()
        self._ready = concurrent.futures.Future()
        self._closed = asyncio.Event()
        self._runner_future = asyncio.run_coroutine_threadsafe(self._run_session(), self._loop)
        try:
            self._ready.result(self._connect_timeout)
        except Exception as exc:
            self._shutdown_loop()
            raise McpConnectionError(f"failed to connect to MCP server: {_message(exc)}") from exc

    async def _run_session(self) -> None:
        """Hold the transport + session open, exiting them in this same task.

        anyio-backed transports (e.g. stdio) require their async context manager
        to be exited in the task that entered it, so connect and teardown both
        live here; ``close`` only flips the ``_closed`` event.
        """
        try:
            async with AsyncExitStack() as stack:
                read, write, *_ = await stack.enter_async_context(self._transport_cm())
                session = _client_session(read, write)
                await stack.enter_async_context(session)
                await session.initialize()
                self._session = session
                self._ready.set_result(None)
                await self._closed.wait()
        except Exception as exc:  # noqa: BLE001 - reported to the waiter
            if not self._ready.done():
                self._ready.set_exception(exc)
        finally:
            self._session = None

    def _await(self, future, timeout: float):
        try:
            return future.result(timeout)
        except McpError:
            raise
        except Exception as exc:
            raise McpCallError(_message(exc)) from exc

    def _shutdown_loop(self) -> None:
        loop = self._loop
        if loop is None:
            return
        self._loop = None
        self._thread = None
        self._session = None
        self._closed = None
        self._ready = None
        self._runner_future = None
        try:
            loop.call_soon_threadsafe(loop.stop)
        except RuntimeError:
            pass

    def close(self) -> None:
        loop = self._loop
        closed = self._closed
        runner = self._runner_future
        if loop is None or closed is None or runner is None:
            self._shutdown_loop()
            return
        try:
            loop.call_soon_threadsafe(closed.set)
            runner.result(timeout=5.0)
        except Exception:  # noqa: BLE001 - best-effort teardown
            logger.warning("failed to close MCP session", exc_info=True)
        finally:
            self._shutdown_loop()

    # -- McpClient -----------------------------------------------------------

    def list_tools(self) -> list[dict]:
        self._ensure()
        future = asyncio.run_coroutine_threadsafe(self._list_tools(), self._loop)
        return self._await(future, self._call_timeout)

    async def _list_tools(self) -> list[dict]:
        result = await self._session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.input_schema or {},
            }
            for tool in result.tools
        ]

    def call_tool(self, name: str, arguments: dict) -> dict:
        self._ensure()
        future = asyncio.run_coroutine_threadsafe(self._call_tool(name, arguments), self._loop)
        return self._await(future, self._call_timeout)

    async def _call_tool(self, name: str, arguments: dict) -> dict:
        result = await self._session.call_tool(name, arguments)
        return {"output": _extract_text(result), "is_error": bool(result.is_error)}


class StdioMcpClient(_SessionMcpClient):
    """MCP client over a stdio subprocess (command + args)."""

    def __init__(self, command: str, args: list[str] | None = None, *, env=None, cwd=None, **kwargs):
        super().__init__(**kwargs)
        self._command = command
        self._args = list(args) if args else []
        self._env = env
        self._cwd = cwd

    def _transport_cm(self):
        from mcp import StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(command=self._command, args=self._args, env=self._env, cwd=self._cwd)
        return stdio_client(params)


class HttpMcpClient(_SessionMcpClient):
    """MCP client over an HTTP (streamable) transport."""

    def __init__(self, url: str, **kwargs):
        super().__init__(**kwargs)
        self._url = url

    def _transport_cm(self):
        from mcp.client.streamable_http import streamable_http_client

        return streamable_http_client(self._url)


def _client_session(read, write):
    from mcp import ClientSession

    return ClientSession(read, write)


def mcp_tool_source(spec: str) -> McpToolSource:
    """Build an :class:`McpToolSource` from a CLI ``--mcp`` spec.

    A URL (``http://`` / ``https://``) selects the HTTP transport; anything else
    is treated as a stdio command line (shell-split into command + args).
    """
    if spec.startswith(("http://", "https://")):
        return McpToolSource(HttpMcpClient(spec))
    parts = shlex.split(spec)
    if not parts:
        raise ValueError("empty MCP server spec")
    return McpToolSource(StdioMcpClient(command=parts[0], args=parts[1:]))
