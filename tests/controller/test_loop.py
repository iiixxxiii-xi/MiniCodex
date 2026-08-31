from minicodex.controller.loop import AgentLoop
from minicodex.controller.policies.retry import RequeryPolicy
from minicodex.model.base import ModelError
from minicodex.model.mock import MockModel


class FakeEnv:
    def execute(self, action):
        return {"output": "ok", "returncode": 0}


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
