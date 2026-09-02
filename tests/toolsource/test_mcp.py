"""``McpToolSource``: schema conversion, call forwarding, and error degradation.

Uses a mock MCP client — no real connection to an external server.
"""

from minicodex.toolsource.mcp import (
    McpCallError,
    McpConnectionError,
    McpToolSource,
    _tool_to_schema,
    mcp_tool_source,
)


class MockClient:
    """A fake MCP client that returns scripted tool lists and results."""

    def __init__(self, tools=None, results=None):
        self.tools = list(tools) if tools is not None else []
        self.results = results or {}
        self.calls = []
        self.list_error = None

    def list_tools(self):
        if self.list_error is not None:
            raise self.list_error
        return list(self.tools)

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if name in self.results:
            result = self.results[name]
            if isinstance(result, Exception):
                raise result
            return result
        return {"output": "ok", "is_error": False}

    def close(self):
        pass


def _tool(name, description="desc", input_schema=None):
    return {
        "name": name,
        "description": description,
        "input_schema": input_schema or {"type": "object", "properties": {}},
    }


def test_schema_conversion():
    client = MockClient(
        tools=[_tool("search", "search the web", {"type": "object", "properties": {"q": {"type": "string"}}})]
    )
    source = McpToolSource(client)
    assert source.schemas() == [
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": "search the web",
                "parameters": {"type": "object", "properties": {"q": {"type": "string"}}},
            },
        }
    ]


def test_tool_to_schema_handles_missing_description_and_schema():
    schema = _tool_to_schema({"name": "bare"})
    assert schema["function"]["name"] == "bare"
    assert schema["function"]["description"] == ""
    assert schema["function"]["parameters"] == {}


async def test_call_forwards_and_returns_structured_success():
    client = MockClient(results={"search": {"output": "found it", "is_error": False}})
    source = McpToolSource(client)
    result = await source.call("search", {"q": "x"})
    assert result == {"output": "found it", "returncode": 0, "error": ""}
    assert client.calls == [("search", {"q": "x"})]


async def test_call_marks_server_reported_error_as_failure():
    client = MockClient(results={"search": {"output": "bad", "is_error": True}})
    source = McpToolSource(client)
    result = await source.call("search", {})
    assert result["returncode"] != 0
    assert result["error"] == "bad"


def test_connection_failure_degrades_schemas_to_empty():
    client = MockClient(tools=[_tool("search")])
    client.list_error = McpConnectionError("connection refused")
    source = McpToolSource(client)
    assert source.schemas() == []


async def test_connection_failure_call_returns_structured_error():
    client = MockClient()
    client.list_error = McpConnectionError("connection refused")
    source = McpToolSource(client)
    source.schemas()  # triggers the connection failure
    result = await source.call("search", {})
    assert result["returncode"] != 0
    assert result["error"]
    assert result["retryable"] is True


async def test_call_failure_returns_structured_error_not_raise():
    client = MockClient(results={"search": McpCallError("tool blew up")})
    source = McpToolSource(client)
    result = await source.call("search", {})
    assert result["returncode"] != 0
    assert result["error"] == "tool blew up"


async def test_unexpected_exception_is_degraded_to_structured_error():
    client = MockClient(results={"search": RuntimeError("boom")})
    source = McpToolSource(client)
    result = await source.call("search", {})
    assert result["returncode"] != 0
    assert result["error"]


def test_mcp_tool_source_factory_parses_stdio_spec():
    source = mcp_tool_source("python server.py")
    assert isinstance(source, McpToolSource)


def test_mcp_tool_source_factory_parses_http_spec():
    source = mcp_tool_source("http://127.0.0.1:9000")
    assert isinstance(source, McpToolSource)
