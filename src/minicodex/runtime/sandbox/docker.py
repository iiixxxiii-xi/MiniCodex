"""``DockerRuntime``: execute shell commands in an isolated Docker container.

Mirrors mini-swe-agent's Docker environment: the container is started with
``docker run -d ... sleep`` and commands run via ``docker exec ... bash -lc``.
Each command carries a timeout; on timeout the running command is interrupted.
``cleanup`` (and ``stop``) force-remove the container with ``docker rm -f``.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shlex
import subprocess
import uuid

from pydantic import BaseModel

from minicodex.runtime.tools.common import combine_output, failure, ok

logger = logging.getLogger(__name__)


class DockerError(Exception):
    """A Docker sandbox operation failed (image pull, container start, ...)."""


class DockerRuntimeConfig(BaseModel):
    """Validated configuration for a ``DockerRuntime`` sandbox."""

    image: str
    cwd: str = "/workspace"
    timeout: int = 30
    executable: str = "docker"
    container_timeout: str = "2h"
    pull_timeout: int = 120


class DockerRuntime:
    """Run shell commands inside a throwaway Docker container.

    The constructor starts the container immediately. ``execute`` returns a
    structured result dict of the shape ``{"output", "returncode", "error"}``
    (plus ``retryable`` on failure) and never raises for command-level failures.
    """

    def __init__(
        self,
        image: str,
        *,
        cwd: str = "/workspace",
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
        self.container_id: str | None = None
        self._start_container()

    @property
    def started(self) -> bool:
        return self.container_id is not None

    def _start_container(self) -> None:
        container_name = f"minicodex-{uuid.uuid4().hex[:8]}"
        argv = [
            self.config.executable,
            "run",
            "-d",
            "--name",
            container_name,
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

    async def execute(self, command: str, *, timeout: int | None = None) -> dict:
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

        async def _run() -> subprocess.CompletedProcess:
            return await asyncio.to_thread(
                subprocess.run,
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=effective_timeout,
            )

        try:
            result = await _run()
        except subprocess.TimeoutExpired:
            logger.warning("command timed out after %ss: %s", effective_timeout, command)
            return failure(f"Command timed out after {effective_timeout}s: {command}", retryable=True)
        except FileNotFoundError:
            return failure(f"Docker executable not found: {self.config.executable}", retryable=False)
        output = combine_output(result)
        if result.returncode != 0:
            return failure(
                f"Command exited with code {result.returncode}",
                output=output,
                returncode=result.returncode,
            )
        return ok(output)

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

    def stop(self) -> None:
        self.cleanup()

    def cleanup(self) -> None:
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
