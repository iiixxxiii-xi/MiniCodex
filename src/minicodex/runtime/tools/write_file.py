"""Write a file (creating parent directories) with UTF-8 encoding."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from minicodex.registry.schema import Tool
from minicodex.runtime.tools.common import ToolError, ok, parse_args, tool


class WriteFileArgs(BaseModel):
    path: str
    content: str


@tool
def run(arguments, *, cwd: Path) -> dict:
    args = parse_args(WriteFileArgs, arguments)
    path = (cwd / args.path).resolve()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args.content, encoding="utf-8")
    except OSError as exc:
        raise ToolError(f"Cannot write file {args.path}: {exc}", retryable=False)
    bytes_written = len(args.content.encode("utf-8"))
    return ok(
        f"Wrote {bytes_written} bytes to {args.path}",
        bytes_written=bytes_written,
        path=args.path,
    )


TOOL = Tool(
    name="write_file",
    description="Write a UTF-8 text file, creating parent directories as needed.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path, relative to the workspace root."},
            "content": {"type": "string", "description": "Full file content to write."},
        },
        "required": ["path", "content"],
    },
    annotations={"write": True},
)
