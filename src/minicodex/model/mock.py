from __future__ import annotations

from minicodex.model.base import ModelResponse, ToolCall, Usage


class MockModel:
    """Scripted model for tests. Returns responses from ``script`` in order,
    repeating the last entry once exhausted (so a one-entry script drives the
    loop forever until a budget kicks in). Usage accumulates a fixed token
    count per call.
    """

    def __init__(
        self,
        script: list[dict] | None = None,
        *,
        input_tokens: int = 100,
        output_tokens: int = 50,
    ):
        self.script = list(script) if script else []
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self._cursor = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self._cancelled = False

    async def query(self, messages: list[dict], tools: list[dict]) -> ModelResponse:
        response = self._next()
        self.total_input_tokens += response.usage.input_tokens
        self.total_output_tokens += response.usage.output_tokens
        self.total_cost_usd += response.usage.cost_usd
        return response

    async def stream(self, messages: list[dict], tools: list[dict]):
        yield await self.query(messages, tools)

    async def cancel(self) -> None:
        self._cancelled = True

    def _default_usage(self) -> Usage:
        return Usage(input_tokens=self.input_tokens, output_tokens=self.output_tokens)

    def _next(self) -> ModelResponse:
        if not self.script:
            return ModelResponse(usage=self._default_usage())
        index = min(self._cursor, len(self.script) - 1)
        if self._cursor < len(self.script):
            self._cursor += 1
        raw = self.script[index]
        usage_raw = raw.get("usage") or {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }
        return ModelResponse(
            thought=raw.get("thought", ""),
            tool_calls=[ToolCall(**tc) for tc in raw.get("tool_calls", [])],
            usage=Usage(**usage_raw),
            stop_reason=raw.get("stop_reason", ""),
        )
