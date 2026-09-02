"""``BuiltinToolSource``: wraps a ``Runtime`` + ``ToolRegistry`` as a ``ToolSource``."""

from minicodex.registry.registry import ToolRegistry
from minicodex.registry.schema import Tool
from minicodex.toolsource.base import ToolSource
from minicodex.toolsource.builtin import BuiltinToolSource


class FakeRuntime:
    """A minimal runtime whose ``execute`` records calls."""

    def __init__(self):
        self.calls = []

    def execute(self, action):
        self.calls.append(action)
        return {"output": f"ran {action['name']}", "returncode": 0, "error": ""}

    def schemas(self):
        return [{"type": "function", "function": {"name": "fake", "description": "d", "parameters": {}}}]


def test_builtin_source_exposes_registry_schemas():
    registry = ToolRegistry()
    registry.register(Tool(name="alpha", description="a tool", parameters={"type": "object"}))
    source = BuiltinToolSource(FakeRuntime(), registry=registry)
    schemas = source.schemas()
    assert [s["function"]["name"] for s in schemas] == ["alpha"]


def test_builtin_source_calls_runtime_execute():
    runtime = FakeRuntime()
    source = BuiltinToolSource(runtime, registry=ToolRegistry())
    result = source.call("alpha", {"x": 1})
    assert result == {"output": "ran alpha", "returncode": 0, "error": ""}
    assert runtime.calls == [{"name": "alpha", "arguments": {"x": 1}}]


def test_builtin_source_accepts_explicit_schemas():
    runtime = FakeRuntime()
    source = BuiltinToolSource(
        runtime, schemas=[{"type": "function", "function": {"name": "beta"}}]
    )
    assert [s["function"]["name"] for s in source.schemas()] == ["beta"]


def test_builtin_source_falls_back_to_runtime_schemas():
    runtime = FakeRuntime()
    source = BuiltinToolSource(runtime)
    assert [s["function"]["name"] for s in source.schemas()] == ["fake"]


def test_builtin_source_is_a_tool_source():
    source = BuiltinToolSource(FakeRuntime())
    assert isinstance(source, ToolSource)
