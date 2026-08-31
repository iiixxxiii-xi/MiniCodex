import pytest

from minicodex.registry.registry import DuplicateToolError, ToolRegistry
from minicodex.registry.schema import Tool


def make_tool(name: str, *, annotations: dict | None = None) -> Tool:
    return Tool(
        name=name,
        description=f"tool {name}",
        parameters={"type": "object", "properties": {}},
        annotations=annotations or {},
    )


def test_register_and_resolve():
    r = ToolRegistry()
    r.register(make_tool("read_file"))
    assert r.resolve("read_file").name == "read_file"
    assert r.resolve("nope") is None


def test_schemas_returns_all_tool_schemas_in_order():
    r = ToolRegistry()
    r.register(make_tool("read_file"))
    r.register(make_tool("shell"))
    names = [s["function"]["name"] for s in r.schemas()]
    assert names == ["read_file", "shell"]


def test_annotations_for():
    r = ToolRegistry()
    r.register(make_tool("read_file", annotations={"read_only": True}))
    assert r.annotations_for("read_file") == {"read_only": True}
    assert r.annotations_for("missing") == {}


def test_duplicate_name_raises():
    r = ToolRegistry()
    r.register(make_tool("shell"))
    with pytest.raises(DuplicateToolError):
        r.register(make_tool("shell"))
