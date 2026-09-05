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
    container_cwd: str = "/workspace",
    activate_cmd: str = "",
    http_proxy: str = "",
):
    """Build a runtime for ``sandbox`` (``"local"`` or ``"docker"``).

    ``"docker"`` bind-mounts ``cwd`` into the container at ``container_cwd``
    (``/workspace`` by default; pre-built SWE-bench images use ``/testbed``) and
    raises :class:`~minicodex.runtime.sandbox.docker.DockerError` when the daemon
    is unavailable (callers should fall back to local). ``activate_cmd`` is a
    shell snippet prepended to every in-container command (e.g. to activate a
    conda environment). ``http_proxy`` is passed into the container's env (e.g.
    a host Clash proxy for network-dependent tests). Any other value yields a
    local runtime.
    """
    if sandbox == "docker":
        from minicodex.runtime.sandbox.docker import DockerRuntime

        return DockerRuntime(
            image=image, mount_path=cwd, cwd=container_cwd,
            activate_cmd=activate_cmd, http_proxy=http_proxy,
        )
    return builtin_runtime(cwd=cwd)


__all__ = ["make_runtime"]
