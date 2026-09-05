"""Apply a patch to the workspace.

Two formats are supported:

* a standard unified ``git diff`` (``diff --git`` …), applied with ``git apply``;
* Claude Code's ``*** Begin Patch`` / ``*** Update File: <path>`` / ``*** End
  Patch`` format, which strong models emit natively. That format carries hunks
  whose headers are often a bare ``@@`` (no line numbers) plus context lines, so
  ``git apply`` cannot parse it. We apply it with a context-matching fuzzy
  applier: for each file, reconstruct the hunk's "old" (context + ``-`` lines)
  and "new" (context + ``+`` lines), locate "old" in the file, and splice in
  "new".

Without this, models trained on the Claude tool format (e.g. DeepSeek V4) emit
patches that ``git apply`` rejects with "No valid patches in input", so the agent
can never actually edit a file.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from minicodex.registry.schema import Tool
from minicodex.runtime.tools.common import failure, ok, parse_args, run_subprocess, tool


class ApplyPatchArgs(BaseModel):
    patch: str


def _parse_claude_sections(patch: str) -> list[tuple[str, list[tuple[list[str], list[str]]]]]:
    """Parse a Claude-format patch into ``[(path, [hunks])]``.

    Each hunk is ``(old_lines, new_lines)`` where ``old_lines`` is the file text
    before the edit (context + removed lines) and ``new_lines`` the text after
    (context + added lines). Handles ``Update File`` (and, best-effort,
    ``Add File`` / ``Delete File``).
    """
    lines = patch.splitlines()
    sections: list[tuple[str, list[tuple[list[str], list[str]]]]] = []
    i = 0
    n = len(lines)
    while i < n:
        stripped = lines[i].strip()
        if stripped.startswith("*** Update File:"):
            path = stripped[len("*** Update File:"):].strip()
            i += 1
            hunks, i = _parse_hunks(lines, i)
            sections.append((path, hunks))
            continue
        if stripped.startswith("*** Add File:"):
            path = stripped[len("*** Add File:"):].strip()
            i += 1
            body: list[str] = []
            while i < n and not lines[i].strip().startswith("*** "):
                raw = lines[i]
                if raw.startswith("+"):
                    body.append(raw[1:])
                elif not raw.strip().startswith("@@"):
                    body.append(raw)
                i += 1
            sections.append((path, [([], body)]))
            continue
        if stripped.startswith("*** Delete File:"):
            path = stripped[len("*** Delete File:"):].strip()
            sections.append((path, [(["(delete)"], [])]))
            i += 1
            continue
        i += 1
    return sections


_END_MARKERS = {"*** Update File:", "*** Add File:", "*** Delete File:", "*** End Patch"}


def _parse_hunks(lines, i):
    """Parse hunks starting at ``lines[i]`` until an end marker; return (hunks, next_i)."""
    hunks = []
    n = len(lines)
    while i < n:
        s = lines[i].strip()
        if s in _END_MARKERS:
            break
        if s == "@@" or s.startswith("@@"):
            i += 1
            old: list[str] = []
            new: list[str] = []
            while i < n:
                s2 = lines[i].strip()
                if s2.startswith("@@") or s2 in _END_MARKERS:
                    break
                raw = lines[i]
                if raw.startswith("+"):
                    new.append(raw[1:])
                elif raw.startswith("-"):
                    old.append(raw[1:])
                else:
                    old.append(raw)
                    new.append(raw)
                i += 1
            hunks.append((old, new))
            continue
        i += 1
    return hunks, i


def _find_sequence(haystack: list[str], needle: list[str]) -> int:
    """Return the index of the first contiguous occurrence of ``needle``, else -1."""
    if not needle:
        return -1
    m = len(needle)
    for start in range(len(haystack) - m + 1):
        if haystack[start:start + m] == needle:
            return start
    return -1


def _apply_claude(cwd: Path, patch: str) -> tuple[bool, str]:
    """Fuzzy-apply a Claude-format patch across its files; return (ok, message)."""
    sections = _parse_claude_sections(patch)
    if not sections:
        return False, "no *** Update/Add/Delete File sections found in patch"
    applied = []
    for path, hunks in sections:
        target = (cwd / path).resolve()
        if not (target == cwd.resolve() or cwd.resolve() in target.parents):
            return False, f"refusing to patch outside workspace: {path}"
        if not target.is_file():
            return False, f"file not found: {path}"
        text = target.read_text(encoding="utf-8")
        lines = text.splitlines()
        # Apply hunks bottom-up so earlier edits don't shift later line numbers.
        for old, new in reversed(hunks):
            if old == ["(delete)"]:
                lines = []
                continue
            idx = _find_sequence(lines, old)
            if idx < 0:
                snippet = " / ".join(old[:3])
                return False, f"could not locate context in {path}: {snippet}..."
            lines[idx:idx + len(old)] = new
        target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        applied.append(path)
    return True, f"Applied patch to {len(applied)} file(s): {', '.join(applied)}"


def _strip_markers(patch: str) -> str:
    """Drop stray ``*** Begin/End Patch`` markers (models sometimes mix formats).

    Splits on ``\\n`` (not ``splitlines``) so a trailing newline is preserved —
    ``git apply`` rejects a diff whose final ``+`` line is not newline-terminated.
    """
    kept = [
        line for line in patch.split("\n")
        if line.strip() not in ("*** Begin Patch", "*** End Patch")
    ]
    return "\n".join(kept)


@tool
def run(arguments, *, cwd: Path) -> dict:
    args = parse_args(ApplyPatchArgs, arguments)
    patch = args.patch

    # Claude-format patches go through the fuzzy applier.
    if "*** Update File:" in patch or "*** Add File:" in patch or "*** Delete File:" in patch:
        okk, msg = _apply_claude(cwd, patch)
        if okk:
            return ok(msg)
        return failure(f"Patch failed to apply:\n{msg}", retryable=False)

    # Otherwise try a standard unified diff via git apply (after stripping any
    # stray Claude markers a model may have mixed in).
    clean = _strip_markers(patch)
    proc = run_subprocess(["git", "apply", "-"], cwd=cwd, input_text=clean)
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
    description=(
        "Apply a patch to edit one or more files. Provide either a standard unified "
        "diff (git diff) or the Claude format:\n"
        "*** Begin Patch\n*** Update File: <path>\n@@\n<context and +/- lines>\n*** End Patch"
    ),
    parameters={
        "type": "object",
        "properties": {
            "patch": {"type": "string", "description": "The patch to apply (unified diff or Claude *** Update File format)."},
        },
        "required": ["patch"],
    },
    annotations={"write": True},
)
