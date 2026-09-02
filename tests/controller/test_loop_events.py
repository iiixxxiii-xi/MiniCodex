"""AgentLoop must emit structured events to an optional sink — the event log is
the single source of truth that the eval layer (Phase 9) replays to compute
metrics."""

import asyncio

from minicodex.controller.loop import AgentLoop
from minicodex.core.events import (
    ActionEvent,
    ErrorEvent,
    InvalidToolCallEvent,
    ModelCallEvent,
    ObservationEvent,
    StepEvent,
)
from minicodex.model.base import ModelResponse
from minicodex.model.mock import MockModel


class ListSink:
    def __init__(self):
        self.events = []

    def append(self, event):
        self.events.append(event)


class FakeEnv:
    async def execute(self, action):
        return {"output": "ok", "returncode": 0}


class SlowEnv:
    async def execute(self, action):
        await asyncio.sleep(0.05)
        return {"output": "ok", "returncode": 0}


class SlowModel:
    async def query(self, messages, tools):
        await asyncio.sleep(0.05)
        return ModelResponse(thought="hi")

    async def stream(self, messages, tools):
        yield ModelResponse(thought="hi")

    async def cancel(self):
        pass


async def test_loop_emits_model_call_latency():
    sink = ListSink()
    loop = AgentLoop(model=SlowModel(), env=FakeEnv(), event_sink=sink, model_name="slow")
    await loop.run(task="x")

    model_calls = [e for e in sink.events if isinstance(e, ModelCallEvent)]
    assert len(model_calls) == 1
    assert model_calls[0].latency_ms > 0


async def test_loop_emits_tool_call_latency():
    model = MockModel(script=[
        {"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "ls"}}]},
        {"tool_calls": []},
    ])
    sink = ListSink()
    loop = AgentLoop(model=model, env=SlowEnv(), event_sink=sink)
    await loop.run(task="x")

    observations = [e for e in sink.events if isinstance(e, ObservationEvent)]
    assert len(observations) == 1
    assert observations[0].latency_ms > 0


async def test_loop_emits_model_call_and_step_events():
    model = MockModel(script=[{"tool_calls": []}])
    sink = ListSink()
    loop = AgentLoop(model=model, env=FakeEnv(), event_sink=sink, model_name="mock")
    await loop.run(task="x")

    model_calls = [e for e in sink.events if isinstance(e, ModelCallEvent)]
    steps = [e for e in sink.events if isinstance(e, StepEvent)]
    assert len(model_calls) == 1
    assert model_calls[0].model == "mock"
    assert model_calls[0].input_tokens == 100
    assert len(steps) == 1
    assert steps[0].step_index == 0


async def test_loop_emits_action_and_linked_observation():
    model = MockModel(script=[
        {"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "ls"}}]},
        {"tool_calls": []},
    ])
    sink = ListSink()
    loop = AgentLoop(model=model, env=FakeEnv(), event_sink=sink)
    await loop.run(task="x")

    actions = [e for e in sink.events if isinstance(e, ActionEvent)]
    observations = [e for e in sink.events if isinstance(e, ObservationEvent)]
    assert len(actions) == 1
    assert len(observations) == 1
    assert actions[0].tool_name == "shell"
    assert observations[0].action_id == actions[0].id
    assert observations[0].tool_call_id == "1"


async def test_loop_emits_invalid_tool_call_and_error_events():
    model = MockModel(script=[{"tool_calls": [{"id": "1", "name": "", "arguments": {}}]}])
    sink = ListSink()
    loop = AgentLoop(model=model, env=FakeEnv(), event_sink=sink, max_requeries=2)
    result = await loop.run(task="x")

    assert result.exit_status == "RepeatedFormatError"
    invalid = [e for e in sink.events if isinstance(e, InvalidToolCallEvent)]
    errors = [e for e in sink.events if isinstance(e, ErrorEvent)]
    assert len(invalid) == 3
    assert len(errors) == 3
    assert [e.recoverable for e in errors] == [True, True, False]
    assert all(e.error_type == "FormatError" for e in errors)


async def test_loop_without_sink_emits_nothing():
    model = MockModel(script=[{"tool_calls": []}])
    loop = AgentLoop(model=model, env=FakeEnv())
    result = await loop.run(task="x")
    assert result.exit_status == "finished"
