import json

import pytest

from minicodex.model.base import ModelError
from minicodex.model.openai import OpenAIModel, openai_message_to_response, to_openai_messages


class _StatusError(Exception):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class _FailingClient:
    class chat:
        class completions:
            @staticmethod
            async def create(**kwargs):
                raise _StatusError(400)


class _CapturingClient:
    """A fake OpenAI client that records the kwargs passed to ``create``."""

    def __init__(self):
        self.captured = []
        self.chat = _Chat(self.captured)


class _Chat:
    def __init__(self, capture):
        self.completions = _Completions(capture)


class _Completions:
    def __init__(self, capture):
        self._capture = capture

    async def create(self, **kwargs):
        self._capture.append(kwargs)
        return _FakeResponse()


class _FakeResponse:
    def __init__(self):
        self.choices = [_FakeChoice()]
        self.usage = {"prompt_tokens": 1, "completion_tokens": 1}


class _FakeChoice:
    def __init__(self):
        self.message = {"content": None, "tool_calls": []}
        self.finish_reason = "stop"


def test_to_openai_messages_converts_function_calling():
    messages = [
        {"role": "system", "content": "You are a coding agent."},
        {"role": "user", "content": "do it"},
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "call_1", "name": "shell", "arguments": {"command": "ls"}},
        ]},
        {"role": "tool", "content": "ok", "tool_call_id": "call_1", "tool_name": "shell"},
    ]
    out = to_openai_messages(messages)

    assert out[0] == {"role": "system", "content": "You are a coding agent."}
    assert out[1] == {"role": "user", "content": "do it"}

    assistant = out[2]
    assert assistant["role"] == "assistant"
    tc = assistant["tool_calls"][0]
    assert tc["id"] == "call_1"
    assert tc["type"] == "function"
    assert tc["function"]["name"] == "shell"
    assert json.loads(tc["function"]["arguments"]) == {"command": "ls"}

    tool = out[3]
    assert tool["role"] == "tool"
    assert tool["tool_call_id"] == "call_1"
    assert tool["content"] == "ok"
    assert "tool_name" not in tool
    assert "extra" not in tool


async def test_openai_query_sends_function_calling_protocol():
    client = _CapturingClient()
    model = OpenAIModel(model="gpt-4o-mini", client=client)
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "call_1", "name": "shell", "arguments": {"command": "ls"}},
        ]},
        {"role": "tool", "content": "out", "tool_call_id": "call_1", "tool_name": "shell"},
    ]
    await model.query(messages, tools=[])

    sent = client.captured[0]["messages"]
    tool_msg = sent[3]
    assert tool_msg["role"] == "tool"
    assert "tool_call_id" in tool_msg
    assert tool_msg["tool_call_id"] == "call_1"
    assert tool_msg["content"] == "out"
    assert "tool_name" not in tool_msg
    assert "extra" not in tool_msg

    assistant = sent[2]
    assert assistant["role"] == "assistant"
    assert "tool_calls" in assistant
    assert assistant["tool_calls"][0]["function"]["name"] == "shell"


def test_openai_tool_calls_parsed():
    message = {
        "content": None,
        "tool_calls": [
            {"id": "call_1", "function": {"name": "shell", "arguments": json.dumps({"command": "ls"})}},
        ],
    }
    usage = {"prompt_tokens": 10, "completion_tokens": 20}
    r = openai_message_to_response(message, usage=usage, finish_reason="tool_calls")
    assert r.tool_calls[0].name == "shell"
    assert r.tool_calls[0].arguments == {"command": "ls"}
    assert r.usage.input_tokens == 10
    assert r.usage.output_tokens == 20
    assert r.stop_reason == "tool_calls"


def test_openai_invalid_json_arguments_become_empty_dict():
    message = {
        "content": "hi",
        "tool_calls": [{"id": "c", "function": {"name": "shell", "arguments": "not json"}}],
    }
    r = openai_message_to_response(message)
    assert r.tool_calls[0].arguments == {}


def test_openai_model_instantiates_without_client():
    m = OpenAIModel(model="gpt-4o-mini")
    assert m.model == "gpt-4o-mini"


async def test_openai_model_wraps_client_error():
    m = OpenAIModel(model="gpt-4o-mini", client=_FailingClient())
    with pytest.raises(ModelError):
        await m.query([], [])


async def test_openai_model_cancelled_raises():
    m = OpenAIModel(model="gpt-4o-mini")
    await m.cancel()
    with pytest.raises(ModelError):
        await m.query([], [])
