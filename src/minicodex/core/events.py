from __future__ import annotations
import time, uuid
from enum import Enum
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
