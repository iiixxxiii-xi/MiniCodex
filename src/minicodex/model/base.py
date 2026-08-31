from __future__ import annotations

from typing import Iterator, Protocol

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class ModelResponse(BaseModel):
    thought: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    stop_reason: str = ""


class Model(Protocol):
    def query(self, messages: list[dict], tools: list[dict]) -> ModelResponse: ...
    def stream(self, messages: list[dict], tools: list[dict]) -> Iterator[ModelResponse]: ...
    def cancel(self) -> None: ...


class ModelError(Exception):
    """A model call failed and cannot be recovered by retrying.

    Adapters raise this after classifying and retrying the underlying SDK
    failure, wrapping it in a single readable message for the controller.
    """
