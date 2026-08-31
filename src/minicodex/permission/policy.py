"""Permission policy: decide whether a tool action is ALLOW/ASK/DENY.

The decision combines declarative tool annotations (``read_only`` /
``destructive``) with risk classification of shell commands. Deny is the
fail-closed default when annotations conflict or nothing is declared.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum

from minicodex.permission.risk import RiskLevel, classify
from minicodex.registry.schema import Tool


class Decision(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


class PermissionPolicy:
    """Map a tool + action to an ALLOW / ASK / DENY decision.

    Precedence (most restrictive wins):

    1. ``destructive`` annotation -> DENY
    2. ``read_only`` annotation -> ALLOW
    3. command tools (e.g. ``shell``) -> risk-classify the command
       (HIGH -> DENY, MEDIUM -> ASK, LOW -> ALLOW)
    4. anything else -> ASK
    """

    def __init__(self, *, command_tools: Iterable[str] = ("shell",)) -> None:
        self.command_tools = set(command_tools)

    def decide(self, tool: Tool, action: dict) -> Decision:
        annotations = tool.annotations or {}
        if annotations.get("destructive"):
            return Decision.DENY
        if annotations.get("read_only"):
            return Decision.ALLOW
        if tool.name in self.command_tools:
            return self._decide_command(self._extract_command(action))
        return Decision.ASK

    def _decide_command(self, command: str) -> Decision:
        risk = classify(command)
        if risk is RiskLevel.HIGH:
            return Decision.DENY
        if risk is RiskLevel.MEDIUM:
            return Decision.ASK
        return Decision.ALLOW

    @staticmethod
    def _extract_command(action: dict) -> str:
        arguments = action.get("arguments") or {}
        return arguments.get("command") or action.get("command", "")
