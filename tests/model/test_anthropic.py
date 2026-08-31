import pytest

from minicodex.model.anthropic import AnthropicModel, anthropic_message_to_response
from minicodex.model.base import ModelError


class _StatusError(Exception):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class _FailingClient:
    class messages:
        @staticmethod
        def create(**kwargs):
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


def test_anthropic_model_instantiates_without_client():
    m = AnthropicModel(model="claude-sonnet-4-5")
    assert m.model == "claude-sonnet-4-5"


def test_anthropic_model_wraps_client_error():
    m = AnthropicModel(model="claude-sonnet-4-5", client=_FailingClient())
    with pytest.raises(ModelError):
        m.query([], [])


def test_anthropic_model_cancelled_raises():
    m = AnthropicModel(model="claude-sonnet-4-5")
    m.cancel()
    with pytest.raises(ModelError):
        m.query([], [])
