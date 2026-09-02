"""Tests for the Docker sandbox runtime.

These tests require a running Docker daemon and are skipped automatically when
Docker is unavailable. Run explicitly with ``pytest -m docker``.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from minicodex.runtime.sandbox.docker import DockerRuntime

IMAGE = "python:3.11-slim"


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        subprocess.run(["docker", "info"], capture_output=True, timeout=5, check=True)
    except (subprocess.SubprocessError, OSError):
        return False
    return True


requires_docker = pytest.mark.skipif(not _docker_available(), reason="Docker daemon is unavailable")

pytestmark = [pytest.mark.docker, requires_docker]


async def test_docker_execute_echo_and_cleanup():
    runtime = DockerRuntime(image=IMAGE)
    try:
        result = await runtime.execute("echo hi")
        assert result["returncode"] == 0
        assert "hi" in result["output"]
        assert result["error"] == ""
    finally:
        runtime.cleanup()


async def test_docker_execute_nonzero_exit():
    runtime = DockerRuntime(image=IMAGE)
    try:
        result = await runtime.execute("echo 'oops' >&2; exit 3")
        assert result["returncode"] == 3
        assert result["error"]
    finally:
        runtime.cleanup()


async def test_docker_execute_timeout_is_retryable():
    runtime = DockerRuntime(image=IMAGE)
    try:
        result = await runtime.execute("sleep 5", timeout=1)
        assert result["error"]
        assert result["retryable"] is True
    finally:
        runtime.cleanup()
