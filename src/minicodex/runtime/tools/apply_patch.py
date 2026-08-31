"""Apply a unified diff patch to the workspace using ``git apply``."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from minicodex.registry.schema import Tool
from minicodex.runtime.tools.common import failure, ok, parse_args, run_subprocess, tool


class ApplyPatchArgs(BaseModel):
    patch: str


@tool
def run(arguments, *, cwd: Path) -> dict:
    args = parse_args(ApplyPatchArgs, arguments)
    proc = run_subprocess(["git", "apply", "-"], cwd=cwd, input_text=args.patch)
    if proc.returncode != 0:
        return failure(
            f"Patch failed to apply:\n{proc.stderr.strip()}",
            retryable=False,
            output=proc.stdout,
            returncode=proc.returncode,
        )
    return ok(proc.stdout or "Patch applied successfully.")


TOOL = Tool(
    name="apply_patch",
    description="Apply a unified diff patch to the workspace using 'git apply'.",
    parameters={
        "type": "object",
        "properties": {
            "patch": {"type": "string", "description": "The unified diff patch to apply."},
        },
        "required": ["patch"],
    },
    annotations={"write": True},
)
