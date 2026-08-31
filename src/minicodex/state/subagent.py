"""Sub-agent spawning with state isolation.

A ``task`` tool delegates work to an ephemeral sub-agent. The sub-agent's state
is a whitelist copy of the parent's: parent ``messages``, ``todos``,
``structured_response``, and any declared private keys are excluded, and the
description becomes the sub-agent's sole opening message. Its result is folded
back into a single structured ``tool`` message (the final assistant text, or a
JSON-serialized ``structured_response`` when present).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pydantic import BaseModel, Field

# State keys never passed to a sub-agent nor returned from it.
EXCLUDED_STATE_KEYS = frozenset({"messages", "todos", "structured_response"})


class SubAgentSpec(BaseModel):
    """Declarative description of a spawnable sub-agent."""

    name: str
    description: str
    system_prompt: str
    tools: list[dict] = Field(default_factory=list)


class UnknownSubAgentError(KeyError):
    """Raised when ``task`` names a sub-agent type that is not registered."""

    def __init__(self, subagent_type: str) -> None:
        super().__init__(f"unknown subagent type: {subagent_type}")
        self.subagent_type = subagent_type


class SubAgentRunner:
    """Spawn sub-agents over isolated state and collapse their results.

    Args:
        specs: The available :class:`SubAgentSpec` definitions.
        private_state_keys: Additional parent-state keys to strip (secrets,
            credentials, anything a sub-agent must not see).
        excluded_keys: State keys always excluded (defaults to
            ``messages``/``todos``/``structured_response``).
    """

    def __init__(
        self,
        specs: list[SubAgentSpec],
        *,
        private_state_keys: frozenset[str] | set[str] = frozenset(),
        excluded_keys: frozenset[str] | set[str] = EXCLUDED_STATE_KEYS,
    ) -> None:
        self.specs = {spec.name: spec for spec in specs}
        self.private_state_keys = frozenset(private_state_keys)
        self.excluded_keys = frozenset(excluded_keys)

    def prepare_state(self, parent_state: dict, description: str) -> dict:
        """Build an isolated sub-agent state from ``parent_state``.

        Non-excluded, non-private keys are carried over; ``messages`` is reset
        to a single user message containing ``description``.
        """
        subagent_state = {
            key: value
            for key, value in parent_state.items()
            if key not in self.excluded_keys and key not in self.private_state_keys
        }
        subagent_state["messages"] = [{"role": "user", "content": description}]
        return subagent_state

    def collapse_result(self, result: dict, tool_call_id: str) -> dict:
        """Fold a sub-agent result into a single structured ``tool`` message.

        ``structured_response`` (if present) is JSON-serialized; otherwise the
        last non-empty assistant message text is used.
        """
        structured = result.get("structured_response")
        if structured is not None:
            content = self._serialize_structured(structured)
        else:
            content = self._last_assistant_text(result.get("messages", []))
        return {"role": "tool", "content": content, "tool_name": "task", "tool_call_id": tool_call_id}

    def invoke(
        self,
        subagent_type: str,
        description: str,
        parent_state: dict,
        tool_call_id: str,
        *,
        run: Callable[[SubAgentSpec, dict], dict],
    ) -> dict:
        """Spawn the named sub-agent and return its collapsed result.

        Args:
            subagent_type: Name of a registered :class:`SubAgentSpec`.
            description: The task handed to the sub-agent (its opening message).
            parent_state: The parent agent's state to whitelist-copy.
            tool_call_id: The parent tool call this spawn answers.
            run: The spawn function, ``run(spec, isolated_state) -> result``.

        Raises:
            UnknownSubAgentError: if ``subagent_type`` is not registered.
            ValueError: if ``tool_call_id`` is empty.
        """
        if subagent_type not in self.specs:
            raise UnknownSubAgentError(subagent_type)
        if not tool_call_id:
            raise ValueError("tool_call_id is required for subagent invocation")
        spec = self.specs[subagent_type]
        isolated_state = self.prepare_state(parent_state, description)
        result = run(spec, isolated_state)
        return self.collapse_result(result, tool_call_id)

    @staticmethod
    def _serialize_structured(structured) -> str:
        if hasattr(structured, "model_dump_json"):
            return structured.model_dump_json()
        return json.dumps(structured)

    @staticmethod
    def _last_assistant_text(messages: list[dict]) -> str:
        for message in reversed(messages):
            if message.get("role") == "assistant":
                text = (message.get("content") or "").strip()
                if text:
                    return text
        return ""
