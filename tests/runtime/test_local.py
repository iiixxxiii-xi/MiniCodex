from pathlib import Path

from minicodex.registry.schema import Tool
from minicodex.runtime.local import LocalRuntime


def make_tool(name: str) -> Tool:
    return Tool(name=name, description=f"tool {name}", parameters={"type": "object", "properties": {}})


def test_execute_dispatches_to_registered_tool(tmp_path):
    rt = LocalRuntime(cwd=tmp_path)

    def echo(arguments, *, cwd):
        return {"output": arguments.get("text", ""), "returncode": 0, "error": ""}

    rt.register(make_tool("echo"), echo)
    result = rt.execute({"name": "echo", "arguments": {"text": "hi"}})
    assert result["output"] == "hi"
    assert result["returncode"] == 0
    assert result["error"] == ""


def test_execute_unknown_tool_returns_error(tmp_path):
    rt = LocalRuntime(cwd=tmp_path)
    result = rt.execute({"name": "nope", "arguments": {}})
    assert result["error"]
    assert result["retryable"] is False


def test_execute_catches_tool_exception(tmp_path):
    rt = LocalRuntime(cwd=tmp_path)

    def boom(arguments, *, cwd):
        raise RuntimeError("kaput")

    rt.register(make_tool("boom"), boom)
    result = rt.execute({"name": "boom", "arguments": {}})
    assert result["error"]
    assert result["returncode"] != 0


def test_start_stop_lifecycle(tmp_path):
    rt = LocalRuntime(cwd=tmp_path)
    assert rt.started is False
    rt.start()
    assert rt.started is True
    rt.stop()
    assert rt.started is False


def test_schemas_reflects_registered_tools(tmp_path):
    rt = LocalRuntime(cwd=tmp_path)
    rt.register(make_tool("read_file"), lambda a, *, cwd: {})
    names = [s["function"]["name"] for s in rt.schemas()]
    assert names == ["read_file"]


def test_tools_operate_within_cwd(tmp_path):
    """A tool receives the runtime's cwd so relative paths resolve correctly."""
    rt = LocalRuntime(cwd=tmp_path)

    def where(arguments, *, cwd):
        return {"output": str(cwd), "returncode": 0, "error": ""}

    rt.register(make_tool("where"), where)
    result = rt.execute({"name": "where", "arguments": {}})
    assert Path(result["output"]) == tmp_path.resolve()
