"""Read a file and return line-numbered text, truncated for long files."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from minicodex.registry.schema import Tool
from minicodex.runtime.tools.common import ToolError, ok, parse_args, tool

TRUNCATION_MARKER = "\n[output truncated]"


class ReadFileArgs(BaseModel):
    path: str
    start_line: int = 1
    end_line: int | None = None
    max_chars: int = 4000


@tool
def run(arguments, *, cwd: Path) -> dict:
    args = parse_args(ReadFileArgs, arguments)
    path = (cwd / args.path).resolve()
    if not path.is_file():
        raise ToolError(f"File not found: {args.path}", retryable=False)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ToolError(f"Cannot read file {args.path}: {exc}", retryable=False)

    lines = text.splitlines()
    start = max(args.start_line, 1)
    end = args.end_line if args.end_line is not None else len(lines)
    window = lines[start - 1 : end]
    numbered = [f"{start + i}:{line}" for i, line in enumerate(window)]

    output = "\n".join(numbered)
    truncated = False
    if len(output) > args.max_chars:
        output = output[: args.max_chars] + TRUNCATION_MARKER
        truncated = True
    return ok(output, truncated=truncated, lines=len(window))


TOOL = Tool(
    name="read_file",
    description="Read a file from the workspace and return its contents with line numbers. Long output is truncated.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path, relative to the workspace root."},
            "start_line": {"type": "integer", "description": "First line to read (1-based)."},
            "end_line": {"type": "integer", "description": "Last line to read, inclusive."},
            "max_chars": {"type": "integer", "description": "Maximum characters to return."},
        },
        "required": ["path"],
    },
    annotations={"read_only": True},
)
