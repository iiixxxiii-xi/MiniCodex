"""Pluggable tool sources for the agent loop.

A ``ToolSource`` decouples tool discovery and execution from the loop, so the
built-in tool set and external MCP servers are interchangeable providers.
"""

from minicodex.toolsource.base import DuplicateToolError, ToolSource, ToolSourceError, source_failure
from minicodex.toolsource.builtin import BuiltinToolSource
from minicodex.toolsource.mcp import (
    HttpMcpClient,
    McpCallError,
    McpClient,
    McpConnectionError,
    McpError,
    McpToolSource,
    StdioMcpClient,
    mcp_tool_source,
)

__all__ = [
    "ToolSource",
    "ToolSourceError",
    "DuplicateToolError",
    "source_failure",
    "BuiltinToolSource",
    "McpToolSource",
    "McpClient",
    "McpError",
    "McpConnectionError",
    "McpCallError",
    "StdioMcpClient",
    "HttpMcpClient",
    "mcp_tool_source",
]
