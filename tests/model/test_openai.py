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


class _Delta:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _StreamChoice:
    def __init__(self, delta):
        self.delta = delta


class _StreamChunk:
    def __init__(self, delta):
        self.choices = [_StreamChoice(delta)]


class _AsyncChunks:
    def __init__(self, chunks):
        self._chunks = list(chunks)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._chunks:
            raise StopAsyncIteration
        return self._chunks.pop(0)


class _StreamingCompletions:
    def __init__(self, chunks):
        self._chunks = chunks
        self.captured = []

    async def create(self, **kwargs):
        self.captured.append(kwargs)
        return _AsyncChunks(self._chunks)


class _StreamingChat:
    def __init__(self, chunks):
        self.completions = _StreamingCompletions(chunks)


class _StreamingClient:
    def __init__(self, chunks):
        self.chat = _StreamingChat(chunks)


async def test_openai_query_sends_strict_tool_schemas():
    client = _CapturingClient()
    model = OpenAIModel(model="gpt-4o-mini", client=client)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "shell",
                "description": "run",
                "parameters": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
            },
        }
    ]
    await model.query([{"role": "user", "content": "hi"}], tools=tools)
    sent = client.captured[0]["tools"][0]
    assert sent["function"]["name"] == "shell"
    assert sent["function"]["strict"] is True
    assert sent["function"]["parameters"]["additionalProperties"] is False
    assert sent["function"]["parameters"]["required"] == ["command"]


class _ToolCallResponse:
    def __init__(self, tool_calls):
        self.choices = [_ToolCallChoice(tool_calls)]
        self.usage = {"prompt_tokens": 1, "completion_tokens": 1}


class _ToolCallChoice:
    def __init__(self, tool_calls):
        self.message = {"content": None, "tool_calls": tool_calls}
        self.finish_reason = "tool_calls"


class _ToolCallCompletions:
    def __init__(self, tool_calls):
        self._tool_calls = tool_calls
        self.captured = []

    async def create(self, **kwargs):
        self.captured.append(kwargs)
        return _ToolCallResponse(self._tool_calls)


class _ToolCallChat:
    def __init__(self, tool_calls):
        self.completions = _ToolCallCompletions(tool_calls)


class _ToolCallClient:
    def __init__(self, tool_calls):
        self.chat = _ToolCallChat(tool_calls)


async def test_openai_query_drops_tool_call_with_invalid_arguments():
    tool_calls = [{"id": "call_1", "function": {"name": "shell", "arguments": '{"command": 123}'}}]
    client = _ToolCallClient(tool_calls)
    model = OpenAIModel(model="gpt-4o-mini", client=client)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "shell",
                "parameters": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
            },
        }
    ]
    result = await model.query([{"role": "user", "content": "hi"}], tools=tools)
    assert result.tool_calls == []


async def test_openai_stream_yields_text_and_tool_call_deltas():
    tool_delta = {
        "index": 0,
        "id": "call_1",
        "type": "function",
        "function": {"name": "shell", "arguments": '{"command": "ls"}'},
    }
    chunks = [
        _StreamChunk(_Delta(content="Let me ")),
        _StreamChunk(_Delta(tool_calls=[tool_delta])),
    ]
    client = _StreamingClient(chunks)
    model = OpenAIModel(model="gpt-4o-mini", client=client)
    out = [chunk async for chunk in model.stream([], [])]

    assert "".join(c.thought for c in out) == "Let me "
    deltas = [d for c in out for d in c.tool_call_deltas]
    assert len(deltas) == 1
    assert deltas[0].index == 0
    assert deltas[0].id == "call_1"
    assert deltas[0].name == "shell"
    assert deltas[0].arguments == '{"command": "ls"}'


def test_openai_message_to_response_preserves_reasoning_content():
    message = {"content": None, "reasoning_content": "Let me think...", "tool_calls": []}
    r = openai_message_to_response(message, finish_reason="stop")
    assert r.reasoning_content == "Let me think..."


def test_openai_message_to_response_defaults_reasoning_content_empty():
    r = openai_message_to_response({"content": "hi"})
    assert r.reasoning_content == ""


def test_to_openai_messages_echoes_reasoning_content():
    messages = [
        {"role": "assistant", "content": "", "reasoning_content": "plan", "tool_calls": []},
    ]
    out = to_openai_messages(messages)
    assert out[0]["reasoning_content"] == "plan"


def test_to_openai_messages_omits_empty_reasoning_content():
    messages = [{"role": "assistant", "content": "done"}]
    out = to_openai_messages(messages)
    assert "reasoning_content" not in out[0]


async def test_openai_query_passes_extra_body_and_tool_choice():
    client = _CapturingClient()
    model = OpenAIModel(
        model="deepseek-v4-flash",
        client=client,
        extra_body={"thinking": {"type": "disabled"}},
        tool_choice="required",
    )
    await model.query([{"role": "user", "content": "hi"}], tools=[])
    sent = client.captured[0]
    assert sent["extra_body"] == {"thinking": {"type": "disabled"}}
    assert sent["tool_choice"] == "required"


async def test_openai_query_defaults_extra_body_and_tool_choice_to_none():
    client = _CapturingClient()
    model = OpenAIModel(model="gpt-4o-mini", client=client)
    await model.query([{"role": "user", "content": "hi"}], tools=[])
    sent = client.captured[0]
    assert sent["extra_body"] is None
    assert sent["tool_choice"] is None


async def test_openai_stream_passes_extra_body_and_tool_choice():
    client = _StreamingClient(chunks=[])
    model = OpenAIModel(
        model="deepseek-v4-flash",
        client=client,
        extra_body={"thinking": {"type": "disabled"}},
        tool_choice="required",
    )
    _ = [chunk async for chunk in model.stream([], [])]
    sent = client.chat.completions.captured[0]
    assert sent["extra_body"] == {"thinking": {"type": "disabled"}}
    assert sent["tool_choice"] == "required"
