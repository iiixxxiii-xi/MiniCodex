from __future__ import annotations

import json
import logging

from minicodex.model.base import ModelError, ModelResponse, ToolCall, ToolCallDelta, Usage
from minicodex.model.retry import with_retry
from minicodex.model.schema import drop_invalid_tool_calls, to_strict_tool_schema
from minicodex.model.usage import compute_cost

logger = logging.getLogger(__name__)


def _get(obj, key, default=None):
    """Read ``key`` from a dict or SDK object (both shapes occur in tests)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def to_openai_messages(messages: list[dict]) -> list[dict]:
    """Translate internal messages into the OpenAI chat-completion protocol.

    The internal format keeps structured tool-call data on assistant messages
    (``tool_calls`` = ``[{id, name, arguments}]``) and a top-level
    ``tool_call_id`` on tool messages. OpenAI expects assistant ``tool_calls``
    wrapped in a ``function`` object (with JSON-stringified arguments) and a
    top-level ``tool_call_id`` on ``tool`` messages. Internal-only fields
    (``tool_name``, ``extra``) are dropped.
    """
    converted: list[dict] = []
    for message in messages:
        role = message.get("role", "")
        content = message.get("content", "")
        if role == "tool":
            converted.append(
                {
                    "role": "tool",
                    "tool_call_id": message.get("tool_call_id", ""),
                    "content": content or "",
                }
            )
        elif role == "assistant":
            entry: dict = {"role": "assistant", "content": content}
            reasoning_content = message.get("reasoning_content", "") or ""
            if reasoning_content:
                entry["reasoning_content"] = reasoning_content
            tool_calls = message.get("tool_calls") or []
            if tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": tc.get("name", ""),
                            "arguments": json.dumps(tc.get("arguments", {}) or {}),
                        },
                    }
                    for tc in tool_calls
                ]
            converted.append(entry)
        else:
            converted.append({"role": role, "content": content or ""})
    return converted


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
        reasoning_content=_get(message, "reasoning_content", "") or "",
        tool_calls=tool_calls,
        usage=Usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=compute_cost(model, input_tokens, output_tokens) if model else 0.0,
        ),
        stop_reason=finish_reason or "",
    )


class OpenAIModel:
    """OpenAI adapter with retry/backoff, error classification, and logging.

    The SDK client is created lazily so the class can be instantiated without an
    API key. The live call path is exercised in the Phase 10 integration smoke
    test; unit tests cover the pure conversion function and failure handling.
    """

    def __init__(
        self,
        model: str,
        *,
        client=None,
        base_url: str | None = None,
        api_key: str | None = None,
        max_attempts: int = 5,
    ):
        self.model = model
        self._client = client
        self.base_url = base_url
        self.api_key = api_key
        self.max_attempts = max_attempts
        self._cancelled = False

    def _get_client(self):
        if self._client is None:
            import openai

            self._client = openai.AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)
        return self._client

    def _ensure_not_cancelled(self) -> None:
        if self._cancelled:
            raise ModelError(f"OpenAI model '{self.model}' request was cancelled.")

    async def query(self, messages: list[dict], tools: list[dict]) -> ModelResponse:
        self._ensure_not_cancelled()
        client = self._get_client()
        payload = to_openai_messages(messages)
        strict_tools = [to_strict_tool_schema(t) for t in tools] if tools else []

        async def call():
            return await client.chat.completions.create(
                model=self.model,
                messages=payload,
                tools=strict_tools,
            )

        try:
            response = await with_retry(call, max_attempts=self.max_attempts, log=logger)
        except Exception as exc:
            raise ModelError(f"OpenAI model '{self.model}' call failed: {exc}") from exc
        choice = response.choices[0]
        result = openai_message_to_response(
            choice.message,
            usage=response.usage,
            finish_reason=choice.finish_reason,
            model=self.model,
        )
        return drop_invalid_tool_calls(result, strict_tools)

    async def stream(self, messages: list[dict], tools: list[dict]):
        self._ensure_not_cancelled()
        client = self._get_client()
        payload = to_openai_messages(messages)
        strict_tools = [to_strict_tool_schema(t) for t in tools] if tools else []
        try:
            stream = await client.chat.completions.create(
                model=self.model,
                messages=payload,
                tools=strict_tools,
                stream=True,
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta is None:
                    continue
                deltas: list[ToolCallDelta] = []
                for tc in delta.tool_calls or []:
                    function = _get(tc, "function") or {}
                    deltas.append(
                        ToolCallDelta(
                            index=int(_get(tc, "index", 0) or 0),
                            id=_get(tc, "id", "") or "",
                            name=_get(function, "name", "") or "",
                            arguments=_get(function, "arguments", "") or "",
                        )
                    )
                thought = delta.content or ""
                if thought or deltas:
                    yield ModelResponse(thought=thought, tool_call_deltas=deltas)
        except Exception as exc:
            raise ModelError(f"OpenAI model '{self.model}' stream failed: {exc}") from exc

    async def cancel(self) -> None:
        self._cancelled = True
        logger.info("OpenAI model '%s' cancellation requested.", self.model)
