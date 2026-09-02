from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict


class ToolCallDelta(BaseModel):
    """A single incremental fragment of a tool call seen during streaming.

    ``arguments`` carries a raw JSON *fragment* (not a complete object): adapters
    emit partial argument text as the provider streams it, and the consumer
    concatenates fragments per ``index`` before parsing. ``id``/``name`` are set
    on the first fragment of a tool call and are empty on subsequent fragments.
    """

    index: int = 0
    id: str = ""
    name: str = ""
    arguments: str = ""


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class ModelResponse(BaseModel):
    thought: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_deltas: list[ToolCallDelta] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    stop_reason: str = ""


class Model(Protocol):
    async def query(self, messages: list[dict], tools: list[dict]) -> ModelResponse: ...
    def stream(self, messages: list[dict], tools: list[dict]) -> AsyncIterator[ModelResponse]: ...
    async def cancel(self) -> None: ...


class ModelError(Exception):
    """A model call failed and cannot be recovered by retrying.

    Adapters raise this after classifying and retrying the underlying SDK
    failure, wrapping it in a single readable message for the controller.
    """
