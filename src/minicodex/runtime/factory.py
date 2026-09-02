"""Runtime factory: turn a sandbox spec into a :class:`Runtime`.

This is the single seam the runner (and CLI) use to pick a sandbox, so tests can
monkeypatch it to avoid starting a real Docker container.
"""

from __future__ import annotations

from pathlib import Path

from minicodex.runtime.local import builtin_runtime


def make_runtime(
    sandbox: str,
    cwd: str | Path,
    *,
    image: str = "python:3.11-slim",
):
    """Build a runtime for ``sandbox`` (``"local"`` or ``"docker"``).

    ``"docker"`` bind-mounts ``cwd`` into the container at ``/workspace`` and
    raises :class:`~minicodex.runtime.sandbox.docker.DockerError` when the daemon
    is unavailable (callers should fall back to local). Any other value yields a
    local runtime.
    """
    if sandbox == "docker":
        from minicodex.runtime.sandbox.docker import DockerRuntime

        return DockerRuntime(image=image, mount_path=cwd, cwd="/workspace")
    return builtin_runtime(cwd=cwd)


__all__ = ["make_runtime"]
