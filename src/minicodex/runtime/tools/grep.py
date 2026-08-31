"""Search files with a regex pattern using pure Python (Windows-safe, no binary)."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

from minicodex.registry.schema import Tool
from minicodex.runtime.tools.common import ToolError, ok, parse_args, tool


class GrepArgs(BaseModel):
    pattern: str
    path: str = "."
    recursive: bool = True
    case_sensitive: bool = True
    max_results: int = 50
    max_chars: int = 4000


def _display(path: Path, cwd: Path) -> str:
    try:
        return str(path.relative_to(cwd))
    except ValueError:
        return str(path)


@tool
def run(arguments, *, cwd: Path) -> dict:
    args = parse_args(GrepArgs, arguments)
    try:
        flags = 0 if args.case_sensitive else re.IGNORECASE
        regex = re.compile(args.pattern, flags)
    except re.error as exc:
        raise ToolError(f"Invalid regex pattern: {exc}", retryable=False)

    root = (cwd / args.path).resolve()
    if not root.exists():
        raise ToolError(f"Path not found: {args.path}", retryable=False)

    if root.is_file():
        files = [root]
    else:
        iterator = root.rglob("*") if args.recursive else root.glob("*")
        files = sorted(p for p in iterator if p.is_file())

    matches: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_num, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                matches.append(f"{_display(path, cwd)}:{line_num}:{line}")
                if len(matches) >= args.max_results:
                    break
        if len(matches) >= args.max_results:
            break

    output = "\n".join(matches)
    truncated = False
    if len(output) > args.max_chars:
        output = output[: args.max_chars] + "\n[output truncated]"
        truncated = True
    return ok(output, matches=len(matches), truncated=truncated)


TOOL = Tool(
    name="grep",
    description="Search files for a regex pattern. Pure-Python, returns file:line:content matches.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern to search for."},
            "path": {"type": "string", "description": "File or directory to search (relative to workspace)."},
            "recursive": {"type": "boolean", "description": "Recurse into subdirectories."},
            "case_sensitive": {"type": "boolean", "description": "Match case-sensitively."},
            "max_results": {"type": "integer", "description": "Maximum matches to return."},
        },
        "required": ["pattern"],
    },
    annotations={"read_only": True},
)
