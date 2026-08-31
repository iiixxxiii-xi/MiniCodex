"""Shared infrastructure for tool functions.

Every tool returns a structured result dict of the shape
``{"output", "returncode", "error", "retryable"}`` and never lets an unhandled
exception escape (the ``tool`` decorator guarantees this). Failures are
classified: transient problems (timeout / connection) are marked retryable;
deterministic problems (bad args, missing file, non-zero exit) are not.
"""

from __future__ import annotations

import functools
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def ok(output: str, **extra: Any) -> dict:
    """Build a success result. Extra keys (e.g. ``matches``) are merged in."""
    result: dict = {"output": output, "returncode": 0, "error": ""}
    result.update(extra)
    return result


def failure(
    error: str,
    *,
    retryable: bool = False,
    output: str = "",
    returncode: int = 1,
) -> dict:
    """Build a failure result with a readable message and retry classification."""
    return {
        "output": output,
        "returncode": returncode,
        "error": error,
        "retryable": retryable,
    }


class ToolError(Exception):
    """A tool failed in a way that should be surfaced, not crash the loop."""

    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.retryable = retryable


# Exception class-name tokens that indicate a transient, retryable failure.
_RETRYABLE_TOKENS = ("Timeout", "TimeoutExpired", "Connection", "ConnectionError")


def classify_error(exc: BaseException) -> bool:
    """Return True when ``exc`` is a transient failure worth retrying."""
    return any(token in type(exc).__qualname__ for token in _RETRYABLE_TOKENS)


def parse_args(model_cls: type[T], arguments: Any) -> T:
    """Validate ``arguments`` against a pydantic model, raising ``ToolError``
    (non-retryable) on invalid input rather than letting ValidationError escape.
    """
    if not isinstance(arguments, dict):
        arguments = {}
    try:
        return model_cls.model_validate(arguments)
    except ValidationError as exc:
        raise ToolError(f"Invalid arguments: {exc}", retryable=False) from exc


def run_subprocess(
    argv: list[str],
    *,
    cwd: Path,
    input_text: str | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess:
    """Run ``argv`` in ``cwd``, capturing output as text.

    A timeout is classified retryable; a missing binary is non-retryable. A
    non-zero exit is NOT raised — the caller inspects ``returncode`` and reports
    it as a result.
    """
    try:
        return subprocess.run(
            argv,
            cwd=str(cwd),
            input=input_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolError(
            f"Command timed out after {timeout}s: {' '.join(argv)}", retryable=True
        ) from exc
    except FileNotFoundError as exc:
        raise ToolError(f"Command not found: {argv[0]}", retryable=False) from exc


def run_shell(
    command: str,
    *,
    cwd: Path,
    timeout: float | None,
) -> subprocess.CompletedProcess:
    """Run a shell command, classifying timeout as a retryable ``ToolError``."""
    try:
        return subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolError(
            f"Command timed out after {timeout}s: {command}", retryable=True
        ) from exc


def combine_output(proc: subprocess.CompletedProcess) -> str:
    """Merge stdout and stderr into one readable string."""
    output = proc.stdout
    if proc.stderr:
        output = f"{output}\n{proc.stderr}" if output else proc.stderr
    return output


def tool(fn: Callable[..., dict]) -> Callable[..., dict]:
    """Wrap a tool function so it always returns a structured result dict.

    ``ToolError`` becomes a classified failure; any other exception becomes an
    unexpected-error failure classified via ``classify_error``.
    """

    @functools.wraps(fn)
    def wrapper(arguments: Any, *, cwd: Path) -> dict:
        try:
            return fn(arguments, cwd=cwd)
        except ToolError as exc:
            return failure(exc.message, retryable=exc.retryable)
        except FileNotFoundError as exc:
            return failure(f"File not found: {exc}", retryable=False)
        except Exception as exc:  # pragma: no cover - defensive last resort
            return failure(f"Unexpected error: {exc}", retryable=classify_error(exc))

    return wrapper
