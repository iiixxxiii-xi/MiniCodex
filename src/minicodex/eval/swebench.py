"""Parse a local SWE-bench JSONL subset into :class:`Task` objects.

Avoids the HuggingFace ``datasets`` dependency entirely: download the JSONL once
and point the loader at the local file. Records are mapped to the harness's task
shape; the SWE-bench-specific fields (``FAIL_TO_PASS``, ``PASS_TO_PASS``,
``test_patch``) are preserved in ``Task.metadata``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from minicodex.eval.task import Task

logger = logging.getLogger(__name__)

# Fields mapped directly onto Task; everything else is preserved in metadata.
_KNOWN_FIELDS = {
    "instance_id",
    "id",
    "repo",
    "problem_statement",
    "instruction",
    "patch",
    "gold_patch",
    "test_command",
    "base_commit",
}


def to_task(record: dict) -> Task:
    """Convert one SWE-bench record dict into a :class:`Task`.

    Raises ``ValueError`` when the record has no ``instance_id`` (or ``id``).
    """
    instance_id = record.get("instance_id") or record.get("id")
    if not instance_id:
        raise ValueError(f"SWE-bench record missing 'instance_id': {record!r}")
    return Task(
        id=instance_id,
        repo=record.get("repo", ""),
        instruction=record.get("problem_statement") or record.get("instruction", ""),
        gold_patch=record.get("patch") or record.get("gold_patch", ""),
        test_command=record.get("test_command", ""),
        base_commit=record.get("base_commit", ""),
        metadata={k: v for k, v in record.items() if k not in _KNOWN_FIELDS},
    )


def parse_swebench_jsonl(path: str | Path) -> list[Task]:
    """Parse a local SWE-bench JSONL file into tasks.

    Malformed lines and records without an ``instance_id`` are skipped with a
    warning (tolerant replay) rather than aborting the whole load. Raises
    ``FileNotFoundError`` when the file is missing.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"SWE-bench file not found: {path}")
    tasks: list[Task] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            logger.warning("skipping malformed line %d in %s: %s", lineno, path, exc)
            continue
        if not isinstance(data, dict):
            logger.warning("skipping non-object line %d in %s", lineno, path)
            continue
        try:
            tasks.append(to_task(data))
        except ValueError as exc:
            logger.warning("skipping invalid record line %d in %s: %s", lineno, path, exc)
    return tasks
