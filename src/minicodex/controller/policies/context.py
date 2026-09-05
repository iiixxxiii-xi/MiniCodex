"""Context policy: a named knob that changes how the loop manages its message
history and tool observations.

Three real strategies are wired to the existing context primitives:

- ``sliding``    — trim the message list to the last ``window`` non-system
  messages (:func:`minicodex.context.sliding.slide`).
- ``truncation`` — truncate each tool observation to ``max_len`` characters
  (:func:`minicodex.context.truncation.truncate_observation`).
- ``compaction`` — summarize old messages and offload their raw text
  (:func:`minicodex.context.compaction.compact`).
- ``none``       — identity (no context management).

The policy is a plain value object so the ablation layer can name it with a
string while the loop/runner apply its real transforms.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from minicodex.context.compaction import compact
from minicodex.context.sliding import slide
from minicodex.context.truncation import truncate_observation

CONTEXT_POLICIES = ("none", "sliding", "truncation", "compaction")


def _default_summarizer(messages: list[dict]) -> str:
    """Summarizer: keep the meat of tool observations, trim assistant thoughts.

    Tool messages carry the exploration findings (file contents, grep hits,
    shell output) — the exact thing the model needs to keep reasoning about the
    bug. Assistant messages are the model's own chain-of-thought, which can be
    safely trimmed. Truncating tool observations to 200 chars (the old behaviour)
    threw away the relevant code, which is why compaction scored 0%.
    """
    parts = []
    for message in messages:
        content = message.get("content", "") or ""
        role = message.get("role", "")
        if role == "tool":
            parts.append(content[:3000])
        elif content:
            parts.append(content[:300])
    return "\n\n".join(parts)


@dataclass
class ContextPolicy:
    """Dispatch a named context strategy to concrete message/observation transforms."""

    name: str = "none"
    window: int = 20
    max_len: int = 8000
    # How many recent non-system messages to keep verbatim; compaction triggers
    # only once the history exceeds this. OpenHands' condenser uses ~120 events
    # before summarizing; a value of 10 (the old default) triggered compaction
    # every ~10 messages and wrecked the model's context.
    keep_recent: int = 50
    summarizer: Callable[[list[dict]], str] = field(default_factory=lambda: _default_summarizer)
    offload_dir: str | Path | None = None

    def __post_init__(self) -> None:
        if self.name not in CONTEXT_POLICIES:
            raise ValueError(
                f"unknown context policy '{self.name}'; expected one of {CONTEXT_POLICIES}"
            )

    async def process_messages(self, messages: list[dict]) -> list[dict]:
        """Transform the full message list after a step (sliding / compaction)."""
        if self.name == "sliding":
            return slide(messages, self.window)
        if self.name == "compaction":
            result = await compact(
                messages,
                self.summarizer,
                self._offload_dir(),
                keep_recent=self.keep_recent,
            )
            return result.messages
        return messages

    def process_observation(self, text: str) -> str:
        """Transform a single tool observation before it enters the history."""
        if self.name == "truncation":
            return truncate_observation(text, self.max_len)
        return text

    def _offload_dir(self) -> str | Path:
        if self.offload_dir is not None:
            return self.offload_dir
        return Path(tempfile.gettempdir()) / "minicodex-compaction"
