"""``DockerRuntime``: execute shell commands in an isolated Docker container.

Mirrors mini-swe-agent's Docker environment: the container is started with
``docker run -d ... sleep`` and commands run via ``docker exec ... bash -lc``.
Each command carries a timeout; on timeout the running command is interrupted.

When a host ``mount_path`` is supplied the workspace is bind-mounted into the
container at ``cwd`` (default ``/workspace``) so a repo checked out on the host
is visible inside the sandbox — this is what lets SWE-bench-style tasks run
``pytest`` against the mounted repo. ``DockerRuntime`` also satisfies the
:class:`~minicodex.runtime.base.Runtime` protocol: it exposes the built-in tool
schemas and dispatches tool actions, running ``shell``/``test_runner`` inside the
container and file tools against the (bind-mounted) host workspace.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shlex
import shutil
import subprocess
import uuid
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from minicodex.registry.registry import ToolRegistry
from minicodex.runtime.tools.common import (
    ToolError,
    classify_error,
    combine_output,
    failure,
    ok,
    parse_args,
)

logger = logging.getLogger(__name__)

DEFAULT_DOCKER_IMAGE = "python:3.11-slim"
DEFAULT_CONTAINER_CWD = "/workspace"


class DockerError(Exception):
    """A Docker sandbox operation failed (image pull, container start, ...)."""


class DockerRuntimeConfig(BaseModel):
    """Validated configuration for a ``DockerRuntime`` sandbox."""

    image: str
    cwd: str = DEFAULT_CONTAINER_CWD
    timeout: int = 30
    executable: str = "docker"
    container_timeout: str = "2h"
    pull_timeout: int = 120


def docker_available(executable: str = "docker", *, timeout: float = 5.0) -> bool:
    """Return True when ``executable`` exists and the Docker daemon responds.

    The daemon is probed with ``docker info`` under a short timeout so a hung
    or misconfigured daemon never blocks a caller for long.
    """
    if shutil.which(executable) is None:
        return False
    try:
        subprocess.run(
            [executable, "info"],
            capture_output=True,
            timeout=timeout,
            check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return True


class DockerRuntime:
    """Run shell commands inside a throwaway Docker container.

    The constructor starts the container immediately. ``run_command`` returns a
    structured result dict of the shape ``{"output", "returncode", "error"}``
    (plus ``retryable`` on failure) and never raises for command-level failures.
    ``execute`` implements the :class:`~minicodex.runtime.base.Runtime` protocol
    and dispatches tool actions.
    """

    def __init__(
        self,
        image: str,
        *,
        mount_path: str | Path | None = None,
        cwd: str = DEFAULT_CONTAINER_CWD,
        timeout: int = 30,
        executable: str | None = None,
        container_timeout: str = "2h",
        pull_timeout: int = 120,
    ) -> None:
        self.config = DockerRuntimeConfig(
            image=image,
            cwd=cwd,
            timeout=timeout,
            executable=executable or os.getenv("MINICODEX_DOCKER_EXECUTABLE", "docker"),
            container_timeout=container_timeout,
            pull_timeout=pull_timeout,
        )
        # The host directory bind-mounted into the container. File tools operate
        # here (changes are visible in the container via the bind mount); shell
        # and test_runner tools run inside the container against this mount.
        self.host_workspace = Path(mount_path).resolve() if mount_path else Path.cwd().resolve()
        # POSIX-normalised host path for the ``-v`` bind-mount argument.
        self._mount_path = self.host_workspace.as_posix() if mount_path else None
        self.container_id: str | None = None
        self._registry = ToolRegistry()
        self._tools: dict[str, Callable] = {}
        self._register_tools()
        self._start_container()

    @property
    def started(self) -> bool:
        return self.container_id is not None

    def _start_container(self) -> None:
        container_name = f"minicodex-{uuid.uuid4().hex[:8]}"
        argv = [self.config.executable, "run", "-d", "--name", container_name]
        if self._mount_path is not None:
            argv += ["-v", f"{self._mount_path}:{self.config.cwd}"]
        argv += [
            "-w",
            self.config.cwd,
            self.config.image,
            "sleep",
            self.config.container_timeout,
        ]
        logger.debug("starting container: %s", shlex.join(argv))
        try:
            result = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.config.pull_timeout,
                check=True,
            )
        except subprocess.TimeoutExpired as exc:
            raise DockerError(
                f"Timed out pulling image '{self.config.image}' after {self.config.pull_timeout}s"
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            raise DockerError(f"Failed to start container: {detail or exc}") from exc
        except FileNotFoundError as exc:
            raise DockerError(f"Docker executable not found: {self.config.executable}") from exc
        self.container_id = result.stdout.strip()
        logger.info("started container %s (%s)", container_name, self.container_id)

    def run_command_sync(self, command: str, *, timeout: float | None = None) -> dict:
        """Run a shell command in the container (blocking); never raises for
        command-level failures."""
        if self.container_id is None:
            return failure("Container is not running.", retryable=False)
        effective_timeout = timeout if timeout is not None else self.config.timeout
        argv = [
            self.config.executable,
            "exec",
            "-w",
            self.config.cwd,
            self.container_id,
            "bash",
            "-lc",
            command,
        ]
        try:
            result = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=effective_timeout,
            )
        except subprocess.TimeoutExpired:
            logger.warning("command timed out after %ss: %s", effective_timeout, command)
            return failure(
                f"Command timed out after {effective_timeout}s: {command}", retryable=True
            )
        except FileNotFoundError:
            return failure(
                f"Docker executable not found: {self.config.executable}", retryable=False
            )
        output = combine_output(result)
        if result.returncode != 0:
            return failure(
                f"Command exited with code {result.returncode}",
                output=output,
                returncode=result.returncode,
            )
        return ok(output)

    async def run_command(self, command: str, *, timeout: float | None = None) -> dict:
        """Async wrapper around :meth:`run_command_sync`."""
        return await asyncio.to_thread(self.run_command_sync, command, timeout=timeout)

    def run_pytest(self, node_ids: list[str], *, timeout: float = 120.0) -> dict[str, bool]:
        """Run each pytest ``node_id`` in the container; return ``{node: passed}``.

        Nodes are run individually so a failure is attributed to the exact test
        that broke (needed to distinguish ``fail_to_pass`` from ``pass_to_pass``).
        """
        results: dict[str, bool] = {}
        for node in node_ids:
            command = f"python -m pytest {shlex.quote(node)} -q --no-header --tb=no"
            result = self.run_command_sync(command, timeout=timeout)
            results[node] = result["returncode"] == 0
        return results

    # -- Runtime protocol ---------------------------------------------------

    def schemas(self) -> list[dict]:
        return self._registry.schemas()

    def start(self) -> None:
        # The container is already running after the constructor; nothing to do.
        logger.info("docker runtime started (container=%s)", self.container_id)

    def stop(self) -> None:
        # Deliberately a no-op: the agent loop calls ``stop`` when it finishes,
        # but the runner still needs the container alive for the hidden test.
        # ``cleanup`` (or the runner's explicit teardown) removes it for real.
        logger.info("docker runtime stop requested (container kept for hidden test)")

    async def execute(self, action: dict) -> dict:
        """Dispatch a tool action, mirroring :class:`~minicodex.runtime.local.LocalRuntime`.

        ``shell`` and ``test_runner`` run inside the container; the file tools
        run against the bind-mounted host workspace.
        """
        name = action.get("name")
        arguments = action.get("arguments", {})
        fn = self._tools.get(name)
        if fn is None:
            logger.warning("unknown tool '%s'", name)
            return failure(f"Unknown tool '{name}'", retryable=False)
        try:
            return await asyncio.to_thread(fn, arguments, cwd=self.host_workspace)
        except ToolError as exc:
            return failure(exc.message, retryable=exc.retryable)
        except Exception as exc:  # pragma: no cover - defensive last resort
            logger.exception("tool '%s' raised", name)
            return failure(f"Tool '{name}' failed: {exc}", retryable=classify_error(exc))

    def _register_tools(self) -> None:
        from minicodex.runtime.tools import BUILTIN_TOOLS

        for tool_def, fn in BUILTIN_TOOLS:
            if tool_def.name == "shell":
                fn = self._container_shell
            elif tool_def.name == "test_runner":
                fn = self._container_test_runner
            self._registry.register(tool_def)
            self._tools[tool_def.name] = fn

    def _container_shell(self, arguments, *, cwd=None) -> dict:
        from minicodex.runtime.tools.shell import ShellArgs

        args = parse_args(ShellArgs, arguments)
        return self.run_command_sync(args.command, timeout=args.timeout)

    def _container_test_runner(self, arguments, *, cwd=None) -> dict:
        from minicodex.runtime.tools.test_runner import RunnerArgs

        args = parse_args(RunnerArgs, arguments)
        return self.run_command_sync(args.command, timeout=args.timeout)

    # -- lifecycle ----------------------------------------------------------

    def interrupt(self) -> None:
        """Force-kill the container's main process without removing it."""
        if self.container_id is not None:
            subprocess.run(
                [self.config.executable, "kill", self.container_id],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

    def cleanup(self) -> None:
        """Remove the container (idempotent)."""
        if self.container_id is not None:
            subprocess.run(
                [self.config.executable, "rm", "-f", self.container_id],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
            logger.info("removed container %s", self.container_id)
            self.container_id = None

    def __del__(self) -> None:  # pragma: no cover - best-effort cleanup
        try:
            self.cleanup()
        except Exception:
            pass


__all__ = [
    "DEFAULT_CONTAINER_CWD",
    "DEFAULT_DOCKER_IMAGE",
    "DockerError",
    "DockerRuntime",
    "DockerRuntimeConfig",
    "docker_available",
]
