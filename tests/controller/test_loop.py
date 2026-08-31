from minicodex.controller.loop import AgentLoop
from minicodex.controller.policies.retry import RequeryPolicy
from minicodex.model.base import ModelError
from minicodex.model.mock import MockModel


class FakeEnv:
    def execute(self, action):
        return {"output": "ok", "returncode": 0}


class ExplodingEnv:
    """An env whose ``execute`` raises an unexpected exception (not a MinicodexError)."""

    def execute(self, action):
        raise RuntimeError("unexpected env failure")


class FailingModel:
    def __init__(self, error=None):
        self.error = error or ModelError("boom")

    def query(self, messages, tools):
        raise self.error

    def stream(self, messages, tools):
        raise self.error

    def cancel(self):
        pass


def test_loop_runs_until_exit():
    model = MockModel(script=[
        {"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "ls"}}]},
        {"tool_calls": []},  # triggers exit
    ])
    loop = AgentLoop(model=model, env=FakeEnv())
    result = loop.run(task="do thing")
    assert result.exit_status == "finished"


def test_loop_builds_function_calling_messages():
    model = MockModel(script=[
        {"tool_calls": [{"id": "call_1", "name": "shell", "arguments": {"command": "ls"}}]},
        {"tool_calls": []},
    ])
    loop = AgentLoop(model=model, env=FakeEnv())
    loop.run(task="do thing")

    assistant = next(m for m in loop.messages if m["role"] == "assistant" and m.get("tool_calls"))
    assert assistant["tool_calls"] == [{"id": "call_1", "name": "shell", "arguments": {"command": "ls"}}]

    tool = next(m for m in loop.messages if m["role"] == "tool")
    assert tool["tool_call_id"] == "call_1"
    assert "tool_call_id" in tool  # top-level, not nested under 'extra'
    assert tool["tool_name"] == "shell"


def test_loop_hits_step_limit():
    model = MockModel(script=[{"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "ls"}}]}])
    loop = AgentLoop(model=model, env=FakeEnv(), step_limit=2)
    result = loop.run(task="x")
    assert result.exit_status == "LimitsExceeded"


def test_loop_repeated_format_error():
    model = MockModel(script=[{"tool_calls": [{"id": "1", "name": "", "arguments": {}}]}])
    loop = AgentLoop(model=model, env=FakeEnv(), max_requeries=2)
    result = loop.run(task="x")
    assert result.exit_status == "RepeatedFormatError"


def test_loop_degrades_on_unexpected_error():
    model = MockModel(script=[{"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "ls"}}]}])
    loop = AgentLoop(model=model, env=ExplodingEnv())
    result = loop.run(task="x")
    assert result.exit_status == "Error"


def test_loop_degrades_on_model_error():
    loop = AgentLoop(model=FailingModel(), env=FakeEnv(), max_requeries=1)
    result = loop.run(task="x")
    assert result.exit_status == "ModelError"


def test_loop_stops_env_on_exit():
    class RecordingEnv:
        def __init__(self):
            self.stopped = False

        def execute(self, action):
            return {"output": "ok"}

        def stop(self):
            self.stopped = True

    env = RecordingEnv()
    model = MockModel(script=[{"tool_calls": []}])
    loop = AgentLoop(model=model, env=env)
    loop.run(task="x")
    assert env.stopped is True


def test_requery_policy_counts_requeries():
    p = RequeryPolicy(max_requeries=2)
    assert p.should_requery() is True
    assert p.should_requery() is True
    assert p.should_requery() is False
    p.reset()
    assert p.should_requery() is True
