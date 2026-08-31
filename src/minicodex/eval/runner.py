"""Runner: turn a :class:`Task` into a trajectory, metrics, and a PASS/FAIL verdict.

The runner drives the :class:`~minicodex.controller.loop.AgentLoop` with an
instrumented event sink, then runs the task's hidden test command in the task
workspace. Exit code 0 means the agent's patch passes (``passed=True``). The
event log (the single source of truth) is persisted alongside a JSON result.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from pydantic import BaseModel, Field

from minicodex.controller.loop import AgentLoop
from minicodex.core.events import Event, EventSource, SubmissionEvent
from minicodex.eval.metrics import RunMetrics, compute_metrics
from minicodex.eval.task import Task
from minicodex.runtime.local import builtin_runtime

logger = logging.getLogger(__name__)


class RunResult(BaseModel):
    """The outcome of running one task."""

    task_id: str
    exit_status: str = ""
    passed: bool = False
    metrics: RunMetrics = Field(default_factory=RunMetrics)
    error: str = ""
    trajectory_path: str | None = None


class _ListSink:
    """Collects events in memory so metrics can be computed from the trajectory."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def append(self, event: Event) -> None:
        self.events.append(event)


class Runner:
    """Run tasks against a model + runtime, producing trajectories and metrics."""

    def __init__(
        self,
        model,
        *,
        runtime=None,
        output_dir: str | Path | None = None,
        step_limit: int = 0,
        token_limit: int = 0,
        cost_limit: float = 0.0,
        max_requeries: int = 3,
        model_name: str = "",
        hidden_test_timeout: float = 120.0,
    ) -> None:
        self.model = model
        self.runtime = runtime
        self.output_dir = Path(output_dir) if output_dir else None
        self.step_limit = step_limit
        self.token_limit = token_limit
        self.cost_limit = cost_limit
        self.max_requeries = max_requeries
        self.model_name = model_name or getattr(model, "model", "") or type(model).__name__
        self.hidden_test_timeout = hidden_test_timeout
        self._ephemeral_dirs: list[Path] = []

    def run(self, task: Task) -> RunResult:
        """Run one task end-to-end and return its result.

        The model drives the loop against the task workspace; the hidden test
        command then decides PASS/FAIL. Metrics are computed from the replayed
        trajectory. On any failure the result is still returned with ``error``
        populated, never an unhandled exception.
        """
        repo_path = self._resolve_repo_path(task)
        runtime = self.runtime or builtin_runtime(cwd=repo_path)
        sink = _ListSink()
        loop = AgentLoop(
            model=self.model,
            env=runtime,
            step_limit=self.step_limit,
            token_limit=self.token_limit,
            cost_limit=self.cost_limit,
            max_requeries=self.max_requeries,
            tools=runtime.schemas(),
            event_sink=sink,
            model_name=self.model_name,
        )

        # The loop owns the env lifecycle: AgentLoop.run() stops the env in its
        # own ``finally``, so the runner only starts it (avoiding a double stop).
        runtime.start()
        output = loop.run(task=task.instruction)

        passed, error, _ = self._run_hidden_test(task, repo_path)
        submission = self._collect_patch(repo_path)
        sink.events.append(
            SubmissionEvent(source=EventSource.CONTROLLER, content=submission, passed=passed)
        )
        metrics = compute_metrics(sink.events)

        result = RunResult(
            task_id=task.id,
            exit_status=output.exit_status,
            passed=passed,
            metrics=metrics,
            error=error,
        )
        if self.output_dir is not None:
            result.trajectory_path = str(self._persist(task, result, sink.events))
        self._cleanup_ephemeral(repo_path)
        return result

    def _resolve_repo_path(self, task: Task) -> Path:
        """Return (and create if missing) the workspace directory for ``task``."""
        if task.repo_path:
            path = Path(task.repo_path)
            path.mkdir(parents=True, exist_ok=True)
            return path.resolve()
        if self.output_dir is not None:
            path = self.output_dir / task.id / "workspace"
            path.mkdir(parents=True, exist_ok=True)
            return path.resolve()
        path = Path(tempfile.mkdtemp(prefix=f"minicodex-{task.id}-"))
        self._ephemeral_dirs.append(path)
        return path

    def _run_hidden_test(self, task: Task, repo_path: Path) -> tuple[bool, str, str]:
        """Run the task's hidden test command; ``returncode == 0`` means pass."""
        if not task.test_command:
            return False, "task has no test_command; cannot determine PASS/FAIL", ""
        try:
            proc = subprocess.run(
                task.test_command,
                shell=True,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.hidden_test_timeout,
            )
        except subprocess.TimeoutExpired:
            logger.warning("hidden test for '%s' timed out", task.id)
            return False, f"hidden test timed out after {self.hidden_test_timeout}s", ""
        except OSError as exc:
            return False, f"hidden test failed to launch: {exc}", ""
        output = proc.stdout or ""
        if proc.stderr:
            output = f"{output}\n{proc.stderr}" if output else proc.stderr
        return proc.returncode == 0, "", output

    def _collect_patch(self, repo_path: Path) -> str:
        """Return the workspace's ``git diff`` (empty when not a git repo)."""
        try:
            proc = subprocess.run(
                ["git", "-C", str(repo_path), "diff"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            if proc.returncode == 0 and proc.stdout:
                return proc.stdout
        except (OSError, subprocess.TimeoutExpired):
            pass
        return ""

    def _persist(self, task: Task, result: RunResult, events: list[Event]) -> Path:
        task_dir = self.output_dir / task.id
        task_dir.mkdir(parents=True, exist_ok=True)
        traj_path = task_dir / "trajectory.jsonl"
        with traj_path.open("w", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False) + "\n")
        (task_dir / "result.json").write_text(
            result.model_dump_json(indent=2), encoding="utf-8"
        )
        return traj_path

    def _cleanup_ephemeral(self, repo_path: Path) -> None:
        for path in self._ephemeral_dirs:
            if path == repo_path:
                shutil.rmtree(path, ignore_errors=True)


__all__ = ["RunResult", "Runner"]
