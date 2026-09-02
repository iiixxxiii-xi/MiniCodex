from minicodex.controller.loop import AgentLoop
from minicodex.controller.policies.retry import RequeryPolicy
from minicodex.model.base import ModelError, ModelResponse, Usage
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


class RecordingStreamModel:
    """Records whether the loop called ``query`` or ``stream``."""

    def __init__(self):
        self.query_calls = 0
        self.stream_calls = 0

    def query(self, messages, tools):
        self.query_calls += 1
        return ModelResponse(thought="query")

    def stream(self, messages, tools):
        self.stream_calls += 1
        yield ModelResponse(thought="stream")

    def cancel(self):
        pass


class ChunkedStreamModel:
    """Yields multiple partial chunks; the loop must merge them."""

    def __init__(self):
        self.stream_calls = 0

    def query(self, messages, tools):
        return ModelResponse(thought="query")

    def stream(self, messages, tools):
        self.stream_calls += 1
        yield ModelResponse(thought="hello ")
        yield ModelResponse(thought="world", usage=Usage(input_tokens=1, output_tokens=2))

    def cancel(self):
        pass


def test_loop_stream_true_uses_stream_not_query():
    model = RecordingStreamModel()
    loop = AgentLoop(model=model, env=FakeEnv(), stream=True)
    result = loop.run(task="x")
    assert result.exit_status == "finished"
    assert model.stream_calls >= 1
    assert model.query_calls == 0


def test_loop_stream_false_uses_query_not_stream():
    model = RecordingStreamModel()
    loop = AgentLoop(model=model, env=FakeEnv(), stream=False)
    result = loop.run(task="x")
    assert result.exit_status == "finished"
    assert model.query_calls >= 1
    assert model.stream_calls == 0


def test_loop_stream_merges_chunks_into_final_response():
    model = ChunkedStreamModel()
    loop = AgentLoop(model=model, env=FakeEnv(), stream=True)
    loop.run(task="x")
    assistant = next(m for m in loop.messages if m["role"] == "assistant")
    assert assistant["content"] == "hello world"
    assert model.stream_calls >= 1


class CountingFailingModel:
    """Raises ``ModelError`` on every call and counts how many times it was hit."""

    def __init__(self):
        self.calls = 0

    def query(self, messages, tools):
        self.calls += 1
        raise ModelError("boom")

    def stream(self, messages, tools):
        self.calls += 1
        raise ModelError("boom")

    def cancel(self):
        pass


class BigObservationEnv:
    def execute(self, action):
        return {"output": "x" * 100_000, "returncode": 0}


def test_requery_policy_none_never_requeries():
    p = RequeryPolicy(max_requeries=3, policy="none")
    assert p.should_requery() is False
    assert p.should_requery() is False


def test_requery_policy_backoff_sleeps():
    sleeps = []
    p = RequeryPolicy(max_requeries=3, policy="backoff", sleep=sleeps.append)
    assert p.should_requery() is True
    assert p.should_requery() is True
    assert p.should_requery() is True
    assert p.should_requery() is False
    assert sleeps == [1.0, 2.0, 4.0]


def test_loop_retry_policy_none_stops_after_one_error():
    model = CountingFailingModel()
    loop = AgentLoop(model=model, env=FakeEnv(), retry_policy="none", max_requeries=5)
    result = loop.run(task="x")
    assert result.exit_status == "ModelError"
    assert model.calls == 1


def test_loop_retry_policy_fixed_requeries():
    model = CountingFailingModel()
    loop = AgentLoop(model=model, env=FakeEnv(), retry_policy="fixed", max_requeries=2)
    result = loop.run(task="x")
    assert result.exit_status == "ModelError"
    assert model.calls == 3  # 1 initial + 2 requeries


def test_loop_context_policy_truncates_observation():
    model = MockModel(script=[
        {"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "ls"}}]},
        {"tool_calls": []},
    ])
    loop = AgentLoop(
        model=model,
        env=BigObservationEnv(),
        context_policy="truncation",
        truncation_limit=50,
    )
    loop.run(task="x")
    tool_msg = next(m for m in loop.messages if m["role"] == "tool")
    assert "truncated" in tool_msg["content"]


def test_loop_context_policy_sliding_drops_old_messages():
    model = MockModel(script=[
        {"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "ls"}}]},
        {"tool_calls": []},
    ])
    loop = AgentLoop(model=model, env=FakeEnv(), context_policy="sliding", context_window=2)
    loop.run(task="x")
    # after each step only the system + last 2 non-system messages remain
    non_system = [m for m in loop.messages if m["role"] != "system"]
    assert len(non_system) <= 2
