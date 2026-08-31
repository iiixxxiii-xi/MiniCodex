"""Append-only JSONL event log — the single source of truth for a run.

Every committed event is one JSON line, flushed immediately, so metrics,
checkpoints, and trajectories can all be derived by replaying this file.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from minicodex.core.events import (
    ActionEvent,
    ErrorEvent,
    Event,
    InvalidToolCallEvent,
    ModelCallEvent,
    ObservationEvent,
    StepEvent,
    SubmissionEvent,
)

logger = logging.getLogger(__name__)


def _subclass_for_kind(kind: str | None) -> type[Event]:
    """Map an event ``kind`` string to its concrete ``Event`` subclass."""
    return {
        "action": ActionEvent,
        "observation": ObservationEvent,
        "model_call": ModelCallEvent,
        "step": StepEvent,
        "invalid_tool_call": InvalidToolCallEvent,
        "error": ErrorEvent,
        "submission": SubmissionEvent,
    }.get(kind or "", Event)


def deserialize_event(data: dict) -> Event:
    """Reconstruct the correct :class:`Event` subclass from a JSON dict.

    Dispatch is keyed on the ``kind`` field; unknown kinds fall back to the
    base ``Event`` so replay never fails on forward-compatible data.
    """
    return _subclass_for_kind(data.get("kind"))(**data)


class EventLog:
    """Append-only, JSONL-backed event store.

    :meth:`append` writes exactly one JSON line per event and flushes it, so a
    crash never loses a committed event. :meth:`replay` reads all events back in
    order, tolerating missing files and malformed lines.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._handle = None

    def _ensure_open(self):
        if self._handle is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = self.path.open("a", encoding="utf-8")
        return self._handle

    def append(self, event: Event) -> None:
        """Serialize ``event`` to one JSON line and flush it to disk."""
        line = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
        handle = self._ensure_open()
        handle.write(line + "\n")
        handle.flush()

    def replay(self) -> list[Event]:
        """Read back all committed events in order.

        Returns an empty list when the file does not exist. Malformed lines are
        skipped with a warning rather than aborting the replay.
        """
        if not self.path.exists():
            return []
        events: list[Event] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as exc:
                    logger.warning("skipping malformed event line %d in %s: %s", lineno, self.path, exc)
                    continue
                if not isinstance(data, dict):
                    logger.warning("skipping non-object event line %d in %s", lineno, self.path)
                    continue
                try:
                    events.append(deserialize_event(data))
                except (ValueError, TypeError) as exc:
                    logger.warning("skipping invalid event line %d in %s: %s", lineno, self.path, exc)
        return events

    def flush(self) -> None:
        """Flush any buffered writes to disk."""
        if self._handle is not None:
            self._handle.flush()

    def close(self) -> None:
        """Release the underlying file handle (idempotent)."""
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def __enter__(self) -> "EventLog":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
