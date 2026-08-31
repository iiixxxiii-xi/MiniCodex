from __future__ import annotations

from minicodex.model.base import ModelResponse, ToolCall, Usage
from minicodex.model.usage import compute_cost


def _get(obj, key, default=None):
    """Read ``key`` from a dict or SDK object (both shapes occur in tests)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def anthropic_message_to_response(message, *, model: str = "") -> ModelResponse:
    """Convert an Anthropic Messages API response into a ModelResponse.

    ``message`` may be the SDK ``Message`` object or a dict with the same shape
    (``content`` blocks, ``usage``, ``stop_reason``).
    """
    thought_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for block in _get(message, "content", []) or []:
        block_type = _get(block, "type")
        if block_type == "text":
            thought_parts.append(_get(block, "text", "") or "")
        elif block_type == "tool_use":
            tool_calls.append(
                ToolCall(
                    id=_get(block, "id", "") or "",
                    name=_get(block, "name", "") or "",
                    arguments=_get(block, "input", {}) or {},
                )
            )
    usage_raw = _get(message, "usage")
    input_tokens = int(_get(usage_raw, "input_tokens", 0) or 0)
    output_tokens = int(_get(usage_raw, "output_tokens", 0) or 0)
    usage = Usage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=compute_cost(model, input_tokens, output_tokens) if model else 0.0,
    )
    return ModelResponse(
        thought="\n".join(thought_parts),
        tool_calls=tool_calls,
        usage=usage,
        stop_reason=_get(message, "stop_reason", "") or "",
    )


class AnthropicModel:
    """Anthropic adapter. The SDK client is created lazily so the class can be
    instantiated without an API key; the live call path is exercised in the
    Phase 10 integration smoke test, not here.
    """

    def __init__(self, model: str, *, client=None, max_tokens: int = 4096):
        self.model = model
        self._client = client
        self.max_tokens = max_tokens
        self._cancelled = False

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def query(self, messages: list[dict], tools: list[dict]) -> ModelResponse:
        client = self._get_client()
        message = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=messages,
            tools=tools,
        )
        return anthropic_message_to_response(message, model=self.model)

    def stream(self, messages: list[dict], tools: list[dict]):
        client = self._get_client()
        with client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=messages,
            tools=tools,
        ) as stream:
            message = stream.get_final_message()
            yield anthropic_message_to_response(message, model=self.model)

    def cancel(self) -> None:
        self._cancelled = True
