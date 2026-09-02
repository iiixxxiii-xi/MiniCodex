from __future__ import annotations

import logging

from minicodex.model.base import ModelError, ModelResponse, ToolCall, Usage
from minicodex.model.retry import with_retry
from minicodex.model.usage import compute_cost

logger = logging.getLogger(__name__)


def _get(obj, key, default=None):
    """Read ``key`` from a dict or SDK object (both shapes occur in tests)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def to_anthropic_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    """Translate internal messages into the Anthropic Messages API shape.

    Returns ``(system_text, messages)``. Internal ``system`` messages are folded
    into the ``system`` string; assistant ``tool_calls`` become ``tool_use``
    content blocks; consecutive ``tool`` messages become a single ``user``
    message of ``tool_result`` blocks (Anthropic requires tool results in a
    ``user`` turn immediately following the assistant's ``tool_use``).
    """
    system_parts: list[str] = []
    converted: list[dict] = []
    pending_tool_results: list[dict] = []

    def flush_tool_results() -> None:
        if pending_tool_results:
            converted.append({"role": "user", "content": list(pending_tool_results)})
            pending_tool_results.clear()

    for message in messages:
        role = message.get("role", "")
        content = message.get("content", "") or ""
        if role == "system":
            system_parts.append(content)
        elif role == "tool":
            pending_tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": message.get("tool_call_id", ""),
                    "content": content,
                }
            )
        elif role == "assistant":
            flush_tool_results()
            blocks: list[dict] = []
            if content:
                blocks.append({"type": "text", "text": content})
            for tc in message.get("tool_calls") or []:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": tc.get("name", ""),
                        "input": tc.get("arguments", {}) or {},
                    }
                )
            converted.append({"role": "assistant", "content": blocks})
        else:
            flush_tool_results()
            converted.append({"role": "user", "content": [{"type": "text", "text": content}]})
    flush_tool_results()
    return "\n".join(system_parts), converted


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
            arguments = _get(block, "input", {}) or {}
            if not isinstance(arguments, dict):
                arguments = {}
            tool_calls.append(
                ToolCall(
                    id=_get(block, "id", "") or "",
                    name=_get(block, "name", "") or "",
                    arguments=arguments,
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
    """Anthropic adapter with retry/backoff, error classification, and logging.

    The SDK client is created lazily so the class can be instantiated without an
    API key. The live call path is exercised in the Phase 10 integration smoke
    test; unit tests cover the pure conversion function and failure handling.
    """

    def __init__(self, model: str, *, client=None, max_tokens: int = 4096, max_attempts: int = 5):
        self.model = model
        self._client = client
        self.max_tokens = max_tokens
        self.max_attempts = max_attempts
        self._cancelled = False

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.AsyncAnthropic()
        return self._client

    def _ensure_not_cancelled(self) -> None:
        if self._cancelled:
            raise ModelError(f"Anthropic model '{self.model}' request was cancelled.")

    async def query(self, messages: list[dict], tools: list[dict]) -> ModelResponse:
        self._ensure_not_cancelled()
        client = self._get_client()
        system, payload = to_anthropic_messages(messages)

        async def call():
            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": payload,
                "tools": tools,
            }
            if system:
                kwargs["system"] = system
            return await client.messages.create(**kwargs)

        try:
            message = await with_retry(call, max_attempts=self.max_attempts, log=logger)
        except Exception as exc:
            raise ModelError(f"Anthropic model '{self.model}' call failed: {exc}") from exc
        return anthropic_message_to_response(message, model=self.model)

    async def stream(self, messages: list[dict], tools: list[dict]):
        self._ensure_not_cancelled()
        client = self._get_client()
        system, payload = to_anthropic_messages(messages)
        try:
            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": payload,
                "tools": tools,
            }
            if system:
                kwargs["system"] = system
            async with client.messages.stream(**kwargs) as stream:
                message = await stream.get_final_message()
                yield anthropic_message_to_response(message, model=self.model)
        except Exception as exc:
            raise ModelError(f"Anthropic model '{self.model}' stream failed: {exc}") from exc

    async def cancel(self) -> None:
        self._cancelled = True
        logger.info("Anthropic model '%s' cancellation requested.", self.model)
