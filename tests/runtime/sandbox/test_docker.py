"""Tests for the Docker sandbox runtime.

These tests require a running Docker daemon and are skipped automatically when
Docker is unavailable. Run explicitly with ``pytest -m docker``.
"""

from __future__ import annotations

import pytest

from minicodex.runtime.sandbox.docker import DockerRuntime, docker_available

IMAGE = "python:3.11-slim"

requires_docker = pytest.mark.skipif(not docker_available(), reason="Docker daemon is unavailable")

pytestmark = [pytest.mark.docker, requires_docker]


async def test_docker_run_command_echo_and_cleanup():
    runtime = DockerRuntime(image=IMAGE)
    try:
        result = await runtime.run_command("echo hi")
        assert result["returncode"] == 0
        assert "hi" in result["output"]
        assert result["error"] == ""
    finally:
        runtime.cleanup()


async def test_docker_run_command_nonzero_exit():
    runtime = DockerRuntime(image=IMAGE)
    try:
        result = await runtime.run_command("echo 'oops' >&2; exit 3")
        assert result["returncode"] == 3
        assert result["error"]
    finally:
        runtime.cleanup()


async def test_docker_run_command_timeout_is_retryable():
    runtime = DockerRuntime(image=IMAGE)
    try:
        result = await runtime.run_command("sleep 5", timeout=1)
        assert result["error"]
        assert result["retryable"] is True
    finally:
        runtime.cleanup()


async def test_docker_mounts_workspace_and_sets_cwd(tmp_path):
    (tmp_path / "hello.txt").write_text("mounted-content", encoding="utf-8")
    runtime = DockerRuntime(image=IMAGE, mount_path=tmp_path)
    try:
        pwd = await runtime.run_command("pwd")
        assert pwd["returncode"] == 0
        assert "/workspace" in pwd["output"]

        cat = await runtime.run_command("cat hello.txt")
        assert cat["returncode"] == 0
        assert "mounted-content" in cat["output"]
    finally:
        runtime.cleanup()


async def test_docker_execute_dispatches_shell_action_in_container():
    runtime = DockerRuntime(image=IMAGE)
    try:
        result = await runtime.execute(
            {"name": "shell", "arguments": {"command": "echo from-container"}}
        )
        assert result["returncode"] == 0
        assert "from-container" in result["output"]
    finally:
        runtime.cleanup()


async def test_docker_execute_file_tool_writes_to_mounted_workspace(tmp_path):
    runtime = DockerRuntime(image=IMAGE, mount_path=tmp_path)
    try:
        result = await runtime.execute(
            {"name": "write_file", "arguments": {"path": "out.txt", "content": "hello from tool"}}
        )
        assert result["returncode"] == 0
        # Written on the host workspace...
        assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "hello from tool"
        # ...and visible in the container via the bind mount.
        cat = await runtime.run_command("cat out.txt")
        assert "hello from tool" in cat["output"]
    finally:
        runtime.cleanup()


async def test_docker_execute_unknown_tool_returns_failure():
    runtime = DockerRuntime(image=IMAGE)
    try:
        result = await runtime.execute({"name": "nope", "arguments": {}})
        assert result["returncode"] == 1
        assert "Unknown tool" in result["error"]
    finally:
        runtime.cleanup()


async def test_docker_run_pytest_returns_per_node_results(tmp_path):
    runtime = DockerRuntime(image=IMAGE, mount_path=tmp_path)
    try:
        nodes = ["tests/test_x.py::test_a", "tests/test_x.py::test_b"]
        results = runtime.run_pytest(nodes, timeout=30)
        assert set(results) == set(nodes)
        # python:3.11-slim ships no pytest, so collection errors -> not passed.
        assert all(v is False for v in results.values())
    finally:
        runtime.cleanup()
