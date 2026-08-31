"""Run a shell command in the workspace, capturing combined output."""

from __future__ import annotations

import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from minicodex.registry.schema import Tool
from minicodex.runtime.tools.common import ToolError, failure, ok, parse_args, tool


class ShellArgs(BaseModel):
    command: str
    timeout: float = Field(default=60.0, gt=0)


@tool
def run(arguments, *, cwd: Path) -> dict:
    args = parse_args(ShellArgs, arguments)
    try:
        proc = subprocess.run(
            args.command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=args.timeout,
        )
    except subprocess.TimeoutExpired:
        raise ToolError(
            f"Command timed out after {args.timeout}s: {args.command}", retryable=True
        )
    output = proc.stdout
    if proc.stderr:
        output = f"{output}\n{proc.stderr}" if output else proc.stderr
    if proc.returncode != 0:
        return failure(
            f"Command exited with code {proc.returncode}",
            retryable=False,
            output=output,
            returncode=proc.returncode,
        )
    return ok(output)


TOOL = Tool(
    name="shell",
    description="Run a shell command in the workspace and return its combined stdout/stderr.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The shell command to run."},
            "timeout": {"type": "number", "description": "Timeout in seconds."},
        },
        "required": ["command"],
    },
    annotations={"shell": True},
)
