"""``ChatRunner``: run one natural-language instruction against a repo.

Chat mode is a thin wrapper over the existing agent stack. Each instruction is
fed to an :class:`~minicodex.controller.loop.AgentLoop` backed by a
:class:`~minicodex.runtime.local.LocalRuntime` rooted at ``--repo``, with the
built-in tool registry. There is no task JSON, gold patch, or hidden test: the
outcome is the agent's ``git diff`` plus a one-line summary for the user to
review themselves.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from minicodex.controller.loop import AgentLoop
from minicodex.core.events import ActionEvent, Event
from minicodex.runtime.local import builtin_runtime

logger = logging.getLogger(__name__)


@dataclass
class ChatTurn:
    """The outcome of one chat instruction."""

    exit_status: str = ""
    diff: str = ""
    tool_calls: list[str] = field(default_factory=list)
    summary: str = ""
    error: str = ""


class _ListSink:
    """Collects loop events in memory so tool activity can be summarised."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def append(self, event: Event) -> None:
        self.events.append(event)


class ChatRunner:
    """Run chat instructions against ``repo`` with a shared model."""

    def __init__(
        self,
        model,
        repo: str | Path,
        *,
        step_limit: int = 0,
        max_requeries: int = 3,
        model_name: str = "",
    ) -> None:
        self.model = model
        self.repo = Path(repo).resolve()
        if not self.repo.is_dir():
            raise ValueError(f"repo directory not found: {self.repo}")
        self.step_limit = step_limit
        self.max_requeries = max_requeries
        self.model_name = model_name or getattr(model, "model", "") or type(model).__name__

    def run(self, instruction: str) -> ChatTurn:
        """Run one instruction and return its diff + summary.

        A fresh runtime + loop is built per turn (the loop owns the env
        lifecycle), so a chat session accumulates edits on the same repo across
        turns. This method never raises on model/tool failures — those are
        already handled by the loop — and only re-raises ``KeyboardInterrupt``.
        """
        try:
            runtime = builtin_runtime(cwd=self.repo)
            sink = _ListSink()
            loop = AgentLoop(
                model=self.model,
                env=runtime,
                step_limit=self.step_limit,
                max_requeries=self.max_requeries,
                tools=runtime.schemas(),
                event_sink=sink,
                model_name=self.model_name,
            )
            runtime.start()
            output = loop.run(task=instruction)
            tool_calls = [event.tool_name for event in sink.events if isinstance(event, ActionEvent)]
            return ChatTurn(
                exit_status=output.exit_status,
                diff=_git_diff(self.repo),
                tool_calls=tool_calls,
                summary=_summarize(output.exit_status, len(tool_calls)),
            )
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # defensive: chat mode must not crash the REPL
            logger.exception("chat turn failed: %s", exc)
            return ChatTurn(exit_status="Error", error=str(exc), summary="agent errored")


def run_chat_session(runner: ChatRunner, *, readline, write) -> int:
    """Drive the interactive REPL, returning a process exit code.

    ``readline()`` yields the next input line (raising ``EOFError`` at end of
    input and ``KeyboardInterrupt`` on Ctrl+C); ``write`` renders each turn.
    Empty input and ``exit``/``quit`` end the session.
    """
    while True:
        try:
            line = readline()
        except (EOFError, KeyboardInterrupt):
            return 0
        text = line.strip()
        if not text or text.lower() in ("exit", "quit"):
            return 0
        try:
            turn = runner.run(text)
        except KeyboardInterrupt:
            return 0
        write(_render_turn(turn))


def _render_turn(turn: ChatTurn) -> str:
    lines = [turn.summary]
    if turn.tool_calls:
        lines.append("tools: " + ", ".join(turn.tool_calls))
    if turn.error:
        lines.append(f"error: {turn.error}")
    if turn.diff:
        lines.append("--- git diff ---")
        lines.append(turn.diff.rstrip("\n"))
    return "\n".join(lines)


def _summarize(exit_status: str, n_tools: int) -> str:
    return f"agent {exit_status} after {n_tools} tool call(s)"


def _git_diff(repo: Path) -> str:
    """Return the workspace's ``git diff`` (empty when not a git repo)."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "diff"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if proc.returncode == 0:
            return proc.stdout
    except (OSError, subprocess.TimeoutExpired):
        logger.warning("failed to collect git diff for %s", repo, exc_info=True)
    return ""
