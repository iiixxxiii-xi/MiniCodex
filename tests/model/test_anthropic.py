import pytest

from minicodex.model.anthropic import AnthropicModel, anthropic_message_to_response, to_anthropic_messages
from minicodex.model.base import ModelError


class _StatusError(Exception):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class _FailingClient:
    class messages:
        @staticmethod
        async def create(**kwargs):
            raise _StatusError(400)


def test_anthropic_text_and_tool_use_blocks():
    message = {
        "content": [
            {"type": "text", "text": "Let me run a command."},
            {"type": "tool_use", "id": "call_1", "name": "shell", "input": {"command": "ls"}},
        ],
        "usage": {"input_tokens": 10, "output_tokens": 20},
        "stop_reason": "tool_use",
    }
    r = anthropic_message_to_response(message)
    assert r.thought == "Let me run a command."
    assert len(r.tool_calls) == 1
    assert r.tool_calls[0].id == "call_1"
    assert r.tool_calls[0].name == "shell"
    assert r.tool_calls[0].arguments == {"command": "ls"}
    assert r.usage.input_tokens == 10
    assert r.usage.output_tokens == 20
    assert r.stop_reason == "tool_use"


def test_anthropic_missing_usage_is_zero():
    message = {"content": [{"type": "text", "text": "hi"}], "usage": None, "stop_reason": "end_turn"}
    r = anthropic_message_to_response(message)
    assert r.usage.input_tokens == 0
    assert r.usage.output_tokens == 0


def test_to_anthropic_messages_converts_function_calling():
    messages = [
        {"role": "system", "content": "You are a coding agent."},
        {"role": "user", "content": "do it"},
        {"role": "assistant", "content": "Let me check.", "tool_calls": [
            {"id": "call_1", "name": "shell", "arguments": {"command": "ls"}},
            {"id": "call_2", "name": "read_file", "arguments": {"path": "a.txt"}},
        ]},
        {"role": "tool", "content": "file1.txt", "tool_call_id": "call_1", "tool_name": "shell"},
        {"role": "tool", "content": "hello", "tool_call_id": "call_2", "tool_name": "read_file"},
        {"role": "assistant", "content": "done", "tool_calls": []},
    ]
    system, converted = to_anthropic_messages(messages)

    assert system == "You are a coding agent."

    assert converted[0] == {"role": "user", "content": [{"type": "text", "text": "do it"}]}

    assistant = converted[1]
    assert assistant["role"] == "assistant"
    assert {"type": "text", "text": "Let me check."} in assistant["content"]
    tool_uses = [b for b in assistant["content"] if b["type"] == "tool_use"]
    assert tool_uses[0] == {"type": "tool_use", "id": "call_1", "name": "shell", "input": {"command": "ls"}}
    assert tool_uses[1]["name"] == "read_file"

    # tool results are grouped into a single user message of tool_result blocks
    results = converted[2]
    assert results["role"] == "user"
    assert results["content"] == [
        {"type": "tool_result", "tool_use_id": "call_1", "content": "file1.txt"},
        {"type": "tool_result", "tool_use_id": "call_2", "content": "hello"},
    ]

    assert converted[3] == {"role": "assistant", "content": [{"type": "text", "text": "done"}]}


def test_anthropic_model_instantiates_without_client():
    m = AnthropicModel(model="claude-sonnet-4-5")
    assert m.model == "claude-sonnet-4-5"


async def test_anthropic_model_wraps_client_error():
    m = AnthropicModel(model="claude-sonnet-4-5", client=_FailingClient())
    with pytest.raises(ModelError):
        await m.query([], [])


async def test_anthropic_model_cancelled_raises():
    m = AnthropicModel(model="claude-sonnet-4-5")
    await m.cancel()
    with pytest.raises(ModelError):
        await m.query([], [])
