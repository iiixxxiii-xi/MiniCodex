from __future__ import annotations

import json

from minicodex.model.base import ModelResponse, ToolCall, Usage
from minicodex.model.usage import compute_cost


def _get(obj, key, default=None):
    """Read ``key`` from a dict or SDK object (both shapes occur in tests)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def openai_message_to_response(
    message, usage=None, finish_reason: str = "", *, model: str = ""
) -> ModelResponse:
    """Convert an OpenAI chat completion choice into a ModelResponse.

    ``message`` is ``response.choices[0].message`` (dict or object), ``usage``
    is ``response.usage``, and ``finish_reason`` is ``choices[0].finish_reason``.
    """
    tool_calls: list[ToolCall] = []
    for tc in _get(message, "tool_calls", []) or []:
        function = _get(tc, "function")
        raw_arguments = _get(function, "arguments", "{}") or "{}"
        try:
            arguments = json.loads(raw_arguments)
        except (TypeError, json.JSONDecodeError):
            arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        tool_calls.append(
            ToolCall(
                id=_get(tc, "id", "") or "",
                name=_get(function, "name", "") or "",
                arguments=arguments,
            )
        )
    input_tokens = int(_get(usage, "prompt_tokens", 0) or 0)
    output_tokens = int(_get(usage, "completion_tokens", 0) or 0)
    return ModelResponse(
        thought=_get(message, "content", "") or "",
        tool_calls=tool_calls,
        usage=Usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=compute_cost(model, input_tokens, output_tokens) if model else 0.0,
        ),
        stop_reason=finish_reason or "",
    )


class OpenAIModel:
    """OpenAI adapter. The SDK client is created lazily so the class can be
    instantiated without an API key; the live call path is exercised in the
    Phase 10 integration smoke test, not here.
    """

    def __init__(self, model: str, *, client=None):
        self.model = model
        self._client = client
        self._cancelled = False

    def _get_client(self):
        if self._client is None:
            import openai

            self._client = openai.OpenAI()
        return self._client

    def query(self, messages: list[dict], tools: list[dict]) -> ModelResponse:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
        )
        choice = response.choices[0]
        return openai_message_to_response(
            choice.message,
            usage=response.usage,
            finish_reason=choice.finish_reason,
            model=self.model,
        )

    def stream(self, messages: list[dict], tools: list[dict]):
        client = self._get_client()
        stream = client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content is not None:
                yield ModelResponse(thought=delta.content)

    def cancel(self) -> None:
        self._cancelled = True
