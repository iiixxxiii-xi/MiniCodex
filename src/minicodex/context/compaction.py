"""Non-destructive context compaction.

Older messages are summarized and their raw text offloaded to a file, so the
conversation window shrinks without losing history: the raw messages remain on
disk and can be replayed via :func:`load_offloaded`.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


class CompactionError(RuntimeError):
    """Raised when raw messages cannot be offloaded to disk."""


@dataclass
class CompactionResult:
    """Outcome of a compaction run.

    Attributes:
        messages: The new, shortened message list (system + summary + recent).
        summary: The plain-text summary of the compacted messages.
        offload_path: Path of the JSONL file holding the raw compacted
            messages, or ``None`` if nothing was compacted.
        compacted: The raw messages that were compacted (for transparency).
    """

    messages: list[dict]
    summary: str
    offload_path: Path | None
    compacted: list[dict] = field(default_factory=list)


def compact(
    messages: list[dict],
    summarizer: Callable[[list[dict]], str],
    offload_dir: str | Path,
    *,
    keep_recent: int = 10,
) -> CompactionResult:
    """Summarize old messages and offload their raw text, keeping recent ones.

    System messages are never compacted. Non-system messages beyond the most
    recent ``keep_recent`` are passed to ``summarizer``, whose result replaces
    them in the returned message list as a single summary message. The raw
    compacted messages are written (one JSON object per line) under
    ``offload_dir`` so no history is lost.

    Returns an unmodified result (``offload_path is None``) when there are at
    most ``keep_recent`` non-system messages.
    """
    system = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]
    if len(non_system) <= keep_recent:
        return CompactionResult(messages=list(messages), summary="", offload_path=None)

    cut = len(non_system) - keep_recent
    compacted = non_system[:cut]
    recent = non_system[cut:]
    summary = summarizer(compacted)
    offload_path = _write_offload(compacted, offload_dir)
    summary_message = {"role": "user", "content": f"[Context summary of earlier conversation]\n{summary}"}
    return CompactionResult(
        messages=system + [summary_message] + recent,
        summary=summary,
        offload_path=offload_path,
        compacted=compacted,
    )


def _write_offload(messages: list[dict], offload_dir: str | Path) -> Path:
    offload_dir = Path(offload_dir)
    offload_dir.mkdir(parents=True, exist_ok=True)
    path = offload_dir / f"compaction-{uuid.uuid4().hex}.jsonl"
    try:
        with path.open("w", encoding="utf-8") as handle:
            for message in messages:
                handle.write(json.dumps(message, ensure_ascii=False) + "\n")
    except OSError as exc:
        raise CompactionError(f"failed to offload raw messages to {path}: {exc}") from exc
    return path


def load_offloaded(path: str | Path) -> list[dict]:
    """Read back raw messages from a compaction offload file.

    Returns an empty list for a missing file and skips malformed lines (logging
    a warning) rather than failing the whole replay.
    """
    path = Path(path)
    if not path.exists():
        return []
    messages: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.warning("skipping malformed offload line %d in %s: %s", lineno, path, exc)
    return messages
