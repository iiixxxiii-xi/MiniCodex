"""Runner: turn a :class:`Task` into a trajectory, metrics, and a PASS/FAIL verdict.

The runner drives the :class:`~minicodex.controller.loop.AgentLoop` with an
instrumented event sink, then runs the task's hidden test command in the task
workspace. Exit code 0 means the agent's patch passes (``passed=True``). The
event log (the single source of truth) is persisted alongside a JSON result.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pydantic import BaseModel, Field

from minicodex.controller.loop import AgentLoop
from minicodex.core.events import Event, EventSource, SubmissionEvent
from minicodex.eval.metrics import RunMetrics, compute_metrics
from minicodex.eval.task import Task
from minicodex.eval.verification import verdict_from_results, verify_workspace
from minicodex.runtime.factory import make_runtime
from minicodex.runtime.local import builtin_runtime
from minicodex.runtime.sandbox.docker import DockerError
from minicodex.toolsource.base import ToolSource
from minicodex.toolsource.builtin import BuiltinToolSource
from minicodex.registry.skill import DEFAULT_SKILLS, select_tool_schemas

logger = logging.getLogger(__name__)


def _is_docker(runtime) -> bool:
    """True when ``runtime`` can run pytest inside a container (a Docker sandbox)."""
    return callable(getattr(runtime, "run_pytest", None))


def _strip_function(source: str, func_name: str) -> str:
    """Remove a top-level ``def func_name`` block (decorators + body) from source.

    Test functions in these tasks are module-level ``def test_*`` blocks; the
    regex matches the optional ``@decorator`` lines, the ``def`` line, and its
    indented body up to the next top-level ``@``/``def`` or end of file.
    """
    pattern = re.compile(
        rf"(?:^@[^\n]*\n)*^def {re.escape(func_name)}\(.*?(?=^(?:@|def) |\Z)",
        re.M | re.S,
    )
    return pattern.sub("", source, count=1)


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
        context_policy: str = "none",
        tool_policy: str = "all",
        skill_loading: bool = False,
        retry_policy: str = "fixed",
        verify: bool = False,
        tool_sources: list[ToolSource] | None = None,
        sandbox: str = "local",
        docker_image: str = "python:3.11-slim",
        container_cwd: str = "/workspace",
        activate_cmd: str = "",
        http_proxy: str = "",
    ) -> None:
        self.model = model
        self.runtime = runtime
        self.sandbox = sandbox
        self.docker_image = docker_image
        self.container_cwd = container_cwd
        self.activate_cmd = activate_cmd
        self.http_proxy = http_proxy
        self.output_dir = Path(output_dir) if output_dir else None
        self.step_limit = step_limit
        self.token_limit = token_limit
        self.cost_limit = cost_limit
        self.max_requeries = max_requeries
        self.model_name = model_name or getattr(model, "model", "") or type(model).__name__
        self.hidden_test_timeout = hidden_test_timeout
        self.context_policy = context_policy
        self.tool_policy = tool_policy
        self.skill_loading = skill_loading
        self.retry_policy = retry_policy
        self.verify = verify
        self.tool_sources = tool_sources
        self._ephemeral_dirs: list[Path] = []

    async def run(self, task: Task) -> RunResult:
        """Run one task end-to-end and return its result.

        The model drives the loop against the task workspace; the hidden test
        command then decides PASS/FAIL. Metrics are computed from the replayed
        trajectory. On any failure the result is still returned with ``error``
        populated, never an unhandled exception.
        """
        repo_path = self._resolve_repo_path(task)
        held_out_tests = self._hide_held_out_tests(repo_path, task)
        runtime = self._build_runtime(repo_path)
        sink = _ListSink()
        schemas = runtime.schemas()
        if self.skill_loading:
            schemas = self._apply_skill_loading(task, schemas)
        filtered = self._apply_tool_policy(schemas)
        tool_sources = None
        if self.tool_sources:
            tool_sources = [BuiltinToolSource(runtime, schemas=filtered), *self.tool_sources]
        verifier = None
        if self.verify:

            def verifier():
                return self._verify_ptp(task, repo_path, runtime)

        loop = AgentLoop(
            model=self.model,
            env=runtime,
            step_limit=self.step_limit,
            token_limit=self.token_limit,
            cost_limit=self.cost_limit,
            max_requeries=self.max_requeries,
            tools=filtered,
            tool_sources=tool_sources,
            event_sink=sink,
            model_name=self.model_name,
            context_policy=self.context_policy,
            retry_policy=self.retry_policy,
            offload_dir=self._offload_dir(),
            verifier=verifier,
        )

        # The loop owns the env lifecycle: AgentLoop.run() stops the env in its
        # own ``finally``, so the runner only starts it (avoiding a double stop).
        # A Docker container is only *removed* in the runner's ``finally`` below,
        # after the hidden test has run inside it.
        try:
            runtime.start()
            output = await loop.run(task=task.instruction)

            self._restore_held_out_tests(repo_path, held_out_tests)
            passed, error, _ = await asyncio.to_thread(
                self._run_hidden_test, task, repo_path, runtime
            )
            submission = await asyncio.to_thread(self._collect_patch, repo_path)
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
            return result
        finally:
            self._restore_held_out_tests(repo_path, held_out_tests)
            self._cleanup_runtime(runtime)
            self._cleanup_ephemeral(repo_path)

    def _resolve_repo_path(self, task: Task) -> Path:
        """Return a fresh, writable workspace for ``task``.

        When ``task.repo_path`` is set its contents are copied to a throwaway
        per-run workspace so the model never mutates the shared buggy baseline
        (SWE-bench style: every run starts from the pristine repo). Otherwise a
        new empty workspace is created.
        """
        if task.repo_path:
            src = Path(task.repo_path)
            # A task may point at a repo that does not exist yet (e.g. a bare
            # ``test_command`` task with no checkout): create it empty rather
            # than failing the copy.
            src.mkdir(parents=True, exist_ok=True)
            path = Path(tempfile.mkdtemp(prefix=f".run-{task.id}-", dir=str(src.parent)))
            shutil.rmtree(path, ignore_errors=True)
            shutil.copytree(
                src,
                path,
                ignore=shutil.ignore_patterns(
                    "__pycache__", "*.pyc", ".pytest_cache", ".git",
                    # Build artifacts from source builds (e.g. matplotlib's
                    # build/freetype-*/...), whose deep paths exceed Windows'
                    # MAX_PATH and make copytree fail with WinError 123.
                    "build", "dist", "*.egg-info", ".tox", ".nox",
                ),
            )
            self._ephemeral_dirs.append(path)
            return path.resolve()
        if self.output_dir is not None:
            path = self.output_dir / task.id / "workspace"
            path.mkdir(parents=True, exist_ok=True)
            return path.resolve()
        path = Path(tempfile.mkdtemp(prefix=f"minicodex-{task.id}-"))
        self._ephemeral_dirs.append(path)
        return path

    def _build_runtime(self, repo_path: Path):
        """Build the runtime for ``repo_path`` from the sandbox spec.

        An explicit ``runtime`` wins. Otherwise ``sandbox == "docker"`` asks the
        factory for a ``DockerRuntime`` (mounting ``repo_path``); a ``DockerError``
        (daemon down, missing image, ...) falls back to a local runtime so a
        failed sandbox never crashes the run.
        """
        if self.runtime is not None:
            return self.runtime
        try:
            return make_runtime(
                self.sandbox,
                repo_path,
                image=self.docker_image,
                container_cwd=self.container_cwd,
                activate_cmd=self.activate_cmd,
                http_proxy=self.http_proxy,
            )
        except DockerError as exc:
            logger.warning(
                "Docker sandbox unavailable (%s); falling back to local sandbox "
                "(pass --sandbox local to silence this).",
                exc,
            )
            return builtin_runtime(cwd=repo_path)

    def _cleanup_runtime(self, runtime) -> None:
        """Remove a disposable sandbox (e.g. a Docker container), if it has one."""
        cleanup = getattr(runtime, "cleanup", None)
        if not callable(cleanup):
            return
        try:
            cleanup()
        except Exception:  # pragma: no cover - best-effort teardown
            logger.warning("failed to clean up runtime %r", runtime, exc_info=True)

    def _apply_tool_policy(self, schemas: list[dict]) -> list[dict]:
        """Filter the function schemas exposed to the model by ``tool_policy``."""
        if self.tool_policy == "no_test_runner":
            return [s for s in schemas if s.get("function", {}).get("name") != "test_runner"]
        return schemas

    def _apply_skill_loading(self, task: Task, schemas: list[dict]) -> list[dict]:
        """Keep only the tool schemas of the skills relevant to ``task``."""
        return select_tool_schemas(task.instruction, schemas, DEFAULT_SKILLS)

    def _offload_dir(self) -> Path | None:
        """Offload directory for compaction (None lets the loop fall back to a temp dir)."""
        if self.context_policy == "compaction" and self.output_dir is not None:
            return self.output_dir / "compaction"
        return None

    def _verify_ptp(self, task: Task, repo_path: Path, runtime=None) -> tuple[bool, str]:
        """Mid-loop verification: run only the P2P (regression) tests.

        The F2P test is held out during the loop (so the model can't invert the
        answer), so a mid-loop verifier can only check regressions — this is the
        "verification" primitive: before accepting ``done``, confirm the patch
        doesn't break existing behaviour.
        """
        nodes = task.pass_to_pass
        if not nodes:
            return True, ""
        if _is_docker(runtime):
            # Batch: run all P2P tests in one invocation (fast for repos with
            # 100+ regression tests, e.g. the pytest repo).
            if runtime.run_tests_all(task.repo, nodes, timeout=self.hidden_test_timeout):
                return True, ""
            return False, "regression failed (pass_to_pass)"
        from minicodex.eval.verification import run_tests

        results = run_tests(repo_path, nodes, timeout=self.hidden_test_timeout)
        failed = [n for n in nodes if not results.get(n, False)]
        if failed:
            return False, f"regression failed: {failed}"
        return True, ""

    def _verify_full(self, task: Task, repo_path: Path, held_out_tests, runtime) -> tuple[bool, str]:
        """Completion verifier: run the full test matrix before accepting ``done``.

        The F2P tests are held out during the loop (so the model can't invert the
        answer), but the *verifier* may run them — it restores the F2P tests,
        runs correctness (F2P) + regression (P2P), then re-hides them before the
        model is queried again. This matches the verifier-agent pattern: verify
        against ground truth, not just "no regression".
        """
        self._restore_held_out_tests(repo_path, held_out_tests)
        try:
            if not runtime.run_tests_all(task.repo, task.fail_to_pass, timeout=self.hidden_test_timeout):
                return False, "your patch does not pass the hidden tests; re-examine and fix it"
            if not runtime.run_tests_all(task.repo, task.pass_to_pass, timeout=self.hidden_test_timeout):
                return False, "your patch breaks existing tests; fix the regression"
        finally:
            self._hide_held_out_tests(repo_path, task)
        return True, ""

    def _run_hidden_test(self, task: Task, repo_path: Path, runtime=None) -> tuple[bool, str, str]:
        """Decide PASS/FAIL for the patched workspace.

        When ``fail_to_pass``/``pass_to_pass`` are populated the SWE-bench style
        test matrix is used: every ``fail_to_pass`` AND every ``pass_to_pass``
        test must pass. Otherwise the legacy ``test_command`` (exit 0) is used.
        When ``runtime`` is a Docker sandbox the tests run inside its container
        (against the mounted repo); otherwise they run on the host.
        """
        if task.fail_to_pass or task.pass_to_pass:
            return self._verify_matrix(task, repo_path, runtime)
        if not task.test_command:
            return False, "task has no test_command; cannot determine PASS/FAIL", ""
        if _is_docker(runtime):
            result = runtime.run_command_sync(task.test_command, timeout=self.hidden_test_timeout)
            if result["returncode"] != 0:
                return False, result["error"] or f"hidden test exited {result['returncode']}", result["output"]
            return True, "", result["output"]
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

    def _verify_matrix(self, task: Task, repo_path: Path, runtime=None) -> tuple[bool, str, str]:
        """Run the task's test matrix (in the sandbox when available) and score it."""
        if _is_docker(runtime):
            # Batch each side (F2P then P2P) in a single invocation rather than
            # per node — a repo like pytest has 100+ regression tests and
            # per-node execution would make the hidden-test phase take ~10 min.
            if not runtime.run_tests_all(task.repo, task.fail_to_pass, timeout=self.hidden_test_timeout):
                return False, "fail_to_pass failed", ""
            if not runtime.run_tests_all(task.repo, task.pass_to_pass, timeout=self.hidden_test_timeout):
                return False, "pass_to_pass failed", ""
            return True, "", ""
        return verify_workspace(task, repo_path, timeout=self.hidden_test_timeout)

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

    def _hide_held_out_tests(self, repo_path: Path, task: Task) -> dict[str, str] | None:
        """Hide the F2P tests (which encode the expected behavior) from the model.

        SWE-bench-style: the ``fail_to_pass`` tests reveal the answer, so strip
        their ``def`` blocks from the test files while keeping the ``pass_to_pass``
        regression tests visible — the agent can still run P2P tests to verify its
        fix (the "verification" primitive). Returns ``{relative_path: original}``
        for restoration, or ``None`` when there is nothing to hide.
        """
        if not task.fail_to_pass:
            return None
        by_file: dict[str, set[str]] = {}
        for node in task.fail_to_pass:
            parts = node.split("::")
            file_rel, func = parts[0], parts[-1]
            if file_rel and func:
                by_file.setdefault(file_rel, set()).add(func)
        held: dict[str, str] = {}
        for file_rel, funcs in by_file.items():
            path = repo_path / file_rel
            if not path.is_file():
                continue
            original = path.read_text(encoding="utf-8")
            stripped = original
            for func in funcs:
                stripped = _strip_function(stripped, func)
            held[file_rel] = original
            path.write_text(stripped, encoding="utf-8")
        return held

    def _restore_held_out_tests(self, repo_path: Path, held: dict[str, str] | None) -> None:
        """Restore the original test-file content hidden by ``_hide_held_out_tests``."""
        if not held:
            return
        for file_rel, original in held.items():
            (repo_path / file_rel).write_text(original, encoding="utf-8")


__all__ = ["RunResult", "Runner"]
