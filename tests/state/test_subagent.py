import json

import pytest
from pydantic import BaseModel

from minicodex.state.subagent import SubAgentRunner, SubAgentSpec, UnknownSubAgentError


def _spec(name="researcher"):
    return SubAgentSpec(name=name, description="researches", system_prompt="You are a researcher.")


def test_prepare_state_isolates_parent_messages_and_private_keys():
    runner = SubAgentRunner([_spec()], private_state_keys={"secret_token"})
    parent = {
        "messages": [{"role": "user", "content": "parent history"}],
        "todos": ["do stuff"],
        "workspace": "/ws",
        "secret_token": "sk-abc",
    }
    state = runner.prepare_state(parent, "do the task")
    assert state["messages"] == [{"role": "user", "content": "do the task"}]
    assert "todos" not in state
    assert "secret_token" not in state
    assert state["workspace"] == "/ws"  # non-private field carried over


def test_collapse_result_extracts_last_assistant_text():
    runner = SubAgentRunner([_spec()])
    result = {
        "messages": [
            {"role": "user", "content": "task"},
            {"role": "assistant", "content": "working..."},
            {"role": "assistant", "content": "final answer"},
        ]
    }
    msg = runner.collapse_result(result, "tc-1")
    assert msg["content"] == "final answer"
    assert msg["role"] == "tool"
    assert msg["tool_call_id"] == "tc-1"
    assert msg["tool_name"] == "task"


def test_collapse_result_skips_trailing_empty_assistant():
    runner = SubAgentRunner([_spec()])
    result = {
        "messages": [
            {"role": "assistant", "content": "the answer"},
            {"role": "assistant", "content": "   "},
        ]
    }
    msg = runner.collapse_result(result, "tc-2")
    assert msg["content"] == "the answer"


def test_collapse_result_prefers_structured_response():
    class Findings(BaseModel):
        summary: str

    runner = SubAgentRunner([_spec()])
    result = {
        "messages": [{"role": "assistant", "content": "ignore me"}],
        "structured_response": Findings(summary="found it"),
    }
    msg = runner.collapse_result(result, "tc-3")
    data = json.loads(msg["content"])
    assert data["summary"] == "found it"


def test_invoke_unknown_subagent_raises():
    runner = SubAgentRunner([_spec("researcher")])
    with pytest.raises(UnknownSubAgentError):
        runner.invoke("nope", "task", {}, "tc", run=lambda spec, state: {"messages": []})


def test_invoke_requires_tool_call_id():
    runner = SubAgentRunner([_spec()])
    with pytest.raises(ValueError):
        runner.invoke("researcher", "task", {}, "", run=lambda spec, state: {"messages": []})


def test_invoke_isolates_and_collapses():
    seen = {}

    def fake_run(spec, state):
        seen["state"] = state
        return {"messages": [{"role": "assistant", "content": "done"}]}

    runner = SubAgentRunner([_spec()], private_state_keys={"secret"})
    parent = {"messages": [{"role": "user", "content": "parent"}], "secret": "x", "workspace": "/ws"}
    msg = runner.invoke("researcher", "do thing", parent, "tc-9", run=fake_run)

    # subagent never saw parent messages or private keys
    assert seen["state"]["messages"] == [{"role": "user", "content": "do thing"}]
    assert "secret" not in seen["state"]
    assert seen["state"]["workspace"] == "/ws"
    # result collapsed to a single structured message
    assert msg == {"role": "tool", "content": "done", "tool_name": "task", "tool_call_id": "tc-9"}
