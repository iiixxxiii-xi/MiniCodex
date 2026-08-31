"""Run read-only git commands (status / diff / log / show) in the workspace."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from minicodex.registry.schema import Tool
from minicodex.runtime.tools.common import failure, ok, parse_args, run_subprocess, tool


class GitArgs(BaseModel):
    args: list[str]


@tool
def run(arguments, *, cwd: Path) -> dict:
    args = parse_args(GitArgs, arguments)
    proc = run_subprocess(["git", *args.args], cwd=cwd)
    if proc.returncode != 0:
        return failure(
            f"git {' '.join(args.args)} failed:\n{proc.stderr.strip()}",
            retryable=False,
            output=proc.stdout,
            returncode=proc.returncode,
        )
    return ok(proc.stdout)


TOOL = Tool(
    name="git",
    description="Run a git subcommand (e.g. status, diff, log, show) in the workspace.",
    parameters={
        "type": "object",
        "properties": {
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "git arguments, e.g. ['status', '--porcelain'].",
            },
        },
        "required": ["args"],
    },
    annotations={"read_only": True},
)
