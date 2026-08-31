from pathlib import Path

from minicodex.controller.loop import AgentLoop
from minicodex.model.mock import MockModel
from minicodex.registry.schema import Tool
from minicodex.runtime.local import LocalRuntime, builtin_runtime


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


def test_builtin_runtime_registers_all_tools(tmp_path):
    rt = builtin_runtime(cwd=tmp_path)
    names = [s["function"]["name"] for s in rt.schemas()]
    assert names == [
        "read_file",
        "write_file",
        "grep",
        "apply_patch",
        "shell",
        "git",
        "test_runner",
    ]


def test_mock_model_and_local_runtime_run_through(tmp_path):
    """End-to-end: MockModel drives a read_file action through the AgentLoop."""
    (tmp_path / "hello.txt").write_text("hello from workspace\n", encoding="utf-8")
    runtime = builtin_runtime(cwd=tmp_path)
    model = MockModel(script=[
        {"tool_calls": [{"id": "c1", "name": "read_file", "arguments": {"path": "hello.txt"}}]},
        {"tool_calls": []},  # triggers exit
    ])
    loop = AgentLoop(model=model, env=runtime, tools=runtime.schemas())
    result = loop.run(task="Read hello.txt")
    assert result.exit_status == "finished"
    observations = [m for m in loop.messages if m["role"] == "tool"]
    assert observations
    assert "hello from workspace" in observations[0]["content"]
