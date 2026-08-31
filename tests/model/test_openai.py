import json

import pytest

from minicodex.model.base import ModelError
from minicodex.model.openai import OpenAIModel, openai_message_to_response


class _StatusError(Exception):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class _FailingClient:
    class chat:
        class completions:
            @staticmethod
            def create(**kwargs):
                raise _StatusError(400)


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


def test_openai_model_wraps_client_error():
    m = OpenAIModel(model="gpt-4o-mini", client=_FailingClient())
    with pytest.raises(ModelError):
        m.query([], [])


def test_openai_model_cancelled_raises():
    m = OpenAIModel(model="gpt-4o-mini")
    m.cancel()
    with pytest.raises(ModelError):
        m.query([], [])
