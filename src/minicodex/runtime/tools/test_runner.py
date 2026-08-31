"""Run the project's test command (default ``pytest -q``) in the workspace."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from minicodex.registry.schema import Tool
from minicodex.runtime.tools.common import combine_output, failure, ok, parse_args, run_shell, tool


class RunnerArgs(BaseModel):
    command: str = "pytest -q"
    timeout: float = Field(default=120.0, gt=0)


@tool
def run(arguments, *, cwd: Path) -> dict:
    args = parse_args(RunnerArgs, arguments)
    proc = run_shell(args.command, cwd=cwd, timeout=args.timeout)
    output = combine_output(proc)
    if proc.returncode != 0:
        return failure(
            f"Tests failed with exit code {proc.returncode}",
            retryable=False,
            output=output,
            returncode=proc.returncode,
        )
    return ok(output)


TOOL = Tool(
    name="test_runner",
    description="Run the project's test command (default 'pytest -q') and return its output.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Test command to run."},
            "timeout": {"type": "number", "description": "Timeout in seconds."},
        },
        "required": [],
    },
    annotations={"shell": True},
)
