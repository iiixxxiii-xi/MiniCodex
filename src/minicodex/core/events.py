from __future__ import annotations
import time, uuid
from enum import Enum
from typing import Protocol
from pydantic import BaseModel, Field


class EventSource(str, Enum):
    CONTROLLER = "controller"
    MODEL = "model"
    TOOL = "tool"
    PERMISSION = "permission"
    RUNTIME = "runtime"
    USER = "user"
    AGENT = "agent"


class Event(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = Field(default_factory=time.time)
    source: EventSource
    kind: str


class EventSink(Protocol):
    """Anything that accepts events, e.g. :class:`minicodex.state.event_log.EventLog`."""

    def append(self, event: Event) -> None: ...


class ActionEvent(Event):
    kind: str = "action"
    tool_name: str
    tool_call_id: str
    action: dict


class ObservationEvent(Event):
    kind: str = "observation"
    tool_name: str
    tool_call_id: str
    action_id: str
    observation: dict


class ModelCallEvent(Event):
    """A completed model query with its token usage and cost."""

    kind: str = "model_call"
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class StepEvent(Event):
    """A completed loop step with its wall-clock duration (milliseconds)."""

    kind: str = "step"
    step_index: int = 0
    duration_ms: float = 0.0


class InvalidToolCallEvent(Event):
    """The model emitted a tool call the controller could not resolve."""

    kind: str = "invalid_tool_call"
    tool_name: str = ""
    reason: str = ""


class ErrorEvent(Event):
    """A recoverable (or exhausted) error caught by the controller."""

    kind: str = "error"
    error_type: str = ""
    recoverable: bool = False
    message: str = ""


class SubmissionEvent(Event):
    """The final submission (patch) and whether the hidden test passed."""

    kind: str = "submission"
    content: str = ""
    passed: bool = False
