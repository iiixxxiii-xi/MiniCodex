"""``AgentLoop`` tool-source integration: merged schemas + per-source dispatch."""

import pytest

from minicodex.controller.loop import AgentLoop
from minicodex.model.base import ModelResponse
from minicodex.model.mock import MockModel
from minicodex.toolsource.base import DuplicateToolError
from minicodex.toolsource.builtin import BuiltinToolSource


class RecordingRuntime:
    def __init__(self):
        self.calls = []

    def execute(self, action):
        self.calls.append(action)
        return {"output": f"builtin:{action['name']}", "returncode": 0, "error": ""}


class EchoSource:
    """A pluggable source that records calls and returns an echo result."""

    def __init__(self, name, tool_name):
        self.name = name
        self.tool_name = tool_name
        self.calls = []

    def schemas(self):
        return [
            {
                "type": "function",
                "function": {"name": self.tool_name, "description": "", "parameters": {}},
            }
        ]

    def call(self, name, arguments):
        self.calls.append((name, arguments))
        return {"output": f"{self.name}:{name}", "returncode": 0, "error": ""}


class CaptureModel:
    def __init__(self):
        self.tools_seen = []

    def query(self, messages, tools):
        self.tools_seen = list(tools)
        return ModelResponse()

    def stream(self, messages, tools):
        self.tools_seen = list(tools)
        return iter([ModelResponse()])

    def cancel(self):
        pass


def test_loop_merges_schemas_from_all_sources():
    runtime = RecordingRuntime()
    builtin = BuiltinToolSource(
        runtime, schemas=[{"type": "function", "function": {"name": "shell"}}]
    )
    mcp = EchoSource("mcp", "search")
    model = CaptureModel()
    loop = AgentLoop(model=model, env=runtime, tool_sources=[builtin, mcp])
    loop.run(task="x")
    names = [s["function"]["name"] for s in model.tools_seen]
    assert names == ["shell", "search"]


def test_loop_dispatches_call_to_matching_source():
    runtime = RecordingRuntime()
    builtin = BuiltinToolSource(
        runtime, schemas=[{"type": "function", "function": {"name": "shell"}}]
    )
    mcp = EchoSource("mcp", "search")
    model = MockModel(
        script=[
            {"tool_calls": [{"id": "1", "name": "search", "arguments": {"q": "x"}}]},
            {"tool_calls": []},
        ]
    )
    loop = AgentLoop(model=model, env=runtime, tool_sources=[builtin, mcp])
    result = loop.run(task="x")
    assert result.exit_status == "finished"
    assert mcp.calls == [("search", {"q": "x"})]
    assert runtime.calls == []  # builtin source was NOT invoked


def test_loop_default_uses_builtin_source():
    runtime = RecordingRuntime()
    model = MockModel(
        script=[
            {"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "ls"}}]},
            {"tool_calls": []},
        ]
    )
    loop = AgentLoop(model=model, env=runtime)
    result = loop.run(task="x")
    assert result.exit_status == "finished"
    assert runtime.calls == [{"name": "shell", "arguments": {"command": "ls"}}]


def test_loop_rejects_duplicate_tool_names_across_sources():
    runtime = RecordingRuntime()
    a = EchoSource("a", "dup")
    b = EchoSource("b", "dup")
    with pytest.raises(DuplicateToolError):
        AgentLoop(model=MockModel(), env=runtime, tool_sources=[a, b])
