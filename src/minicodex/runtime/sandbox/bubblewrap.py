"""Bubblewrap sandbox: Linux-only interface stub.

[Bubblewrap](https://github.com/containers/bubblewrap) (``bwrap``) is an
unprivileged Linux sandboxing tool that requires kernel user-namespace support.
It is not available on Windows (where this project is currently developed), so
this module only defines the interface and deliberately raises if used, rather
than silently running code unsandboxed.

When a Linux implementation is needed, mirror ``DockerRuntime`` but wrap the
command with ``bwrap --unshare-user-try --ro-bind /usr /usr ... --chdir <cwd>
bash -c <command>`` instead of ``docker exec``.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class BubblewrapConfig(BaseModel):
    """Configuration for a (future) ``BubblewrapRuntime`` sandbox."""

    executable: str = "bwrap"
    cwd: str = "/workspace"
    timeout: int = 30


class BubblewrapRuntime:
    """Placeholder for a bubblewrap sandbox. Not implemented: Linux-only.

    ``start`` and ``execute`` raise ``NotImplementedError`` so a caller can
    never mistake this stub for an actual isolation boundary.
    """

    def __init__(self, *, cwd: str = "/workspace", executable: str = "bwrap") -> None:
        self.config = BubblewrapConfig(cwd=cwd, executable=executable)
        logger.warning("BubblewrapRuntime is Linux-only and not implemented; no sandbox is active")

    def start(self) -> None:
        raise NotImplementedError("BubblewrapRuntime is Linux-only and not implemented on this platform.")

    def execute(self, command: str, *, timeout: int | None = None) -> dict:
        raise NotImplementedError("BubblewrapRuntime is Linux-only and not implemented on this platform.")

    def stop(self) -> None:
        return None

    def cleanup(self) -> None:
        return None
