"""Non-destructive context compaction.

Older messages are summarized and their raw text offloaded to a file, so the
conversation window shrinks without losing history: the raw messages remain on
disk and can be replayed via :func:`load_offloaded`.
"""

from __future__ import annotations

import inspect
import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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


def _estimate_tokens(messages: list[dict]) -> int:
    """Rough token estimate (~4 chars/token) for triggering condensation."""
    return sum(len(str(m.get("content", "") or "")) for m in messages) // 4


async def compact(
    messages: list[dict],
    summarizer: Callable[[list[dict]], Any],
    offload_dir: str | Path,
    *,
    keep_recent: int = 50,
    max_tokens: int = 100000,
) -> CompactionResult:
    """Summarize old messages and offload their raw text, keeping recent ones.

    System messages are never compacted. Condensation is triggered only when the
    history's estimated token count exceeds ``max_tokens`` — matching OpenHands'
    condenser, which condenses on a resource limit (``max_tokens``/``max_size``)
    rather than a fixed message count. For short tasks the context never fills
    up, so this is a no-op. Once triggered, messages beyond the most recent
    ``keep_recent`` are summarized (the back half is left untouched), and their
    raw text is offloaded to disk so no history is lost.
    """
    system = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]
    if _estimate_tokens(non_system) <= max_tokens:
        return CompactionResult(messages=list(messages), summary="", offload_path=None)

    # The first non-system message is the task instruction (problem statement);
    # never compact it away — losing it makes the model forget the task.
    head = non_system[:1]
    body = non_system[1:]
    if len(body) <= keep_recent:
        return CompactionResult(messages=list(messages), summary="", offload_path=None)

    cut = len(body) - keep_recent
    # Never split an assistant/tool pair: if the recent window would start with an
    # orphaned "tool" message (its assistant tool_calls would be compacted away),
    # absorb those tool messages into the compacted set instead.
    while cut < len(body) and body[cut].get("role") == "tool":
        cut += 1
    compacted = body[:cut]
    recent = body[cut:]
    summary = summarizer(compacted)
    if inspect.isawaitable(summary):
        summary = await summary
    offload_path = _write_offload(compacted, offload_dir)
    summary_message = {"role": "user", "content": f"[Context summary of earlier conversation]\n{summary}"}
    return CompactionResult(
        messages=system + head + [summary_message] + recent,
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
