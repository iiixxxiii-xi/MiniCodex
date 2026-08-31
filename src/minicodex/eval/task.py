"""Task definition and filesystem loaders.

A :class:`Task` is the unit of evaluation: a repo + instruction the agent must
solve, a reference gold patch, and a hidden test command whose exit code decides
PASS/FAIL. Tasks are stored as JSON (one task per file, or one JSON line per
task in a ``.jsonl``).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)


class Task(BaseModel):
    """A single evaluation task."""

    model_config = ConfigDict(extra="ignore")

    id: str
    repo: str
    instruction: str
    gold_patch: str = ""
    test_command: str = ""
    repo_path: str | None = None
    base_commit: str = ""
    metadata: dict = Field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Build a task from a dict, raising ``ValueError`` on invalid input."""
        try:
            return cls.model_validate(data)
        except ValidationError as exc:
            raise ValueError(f"Invalid task: {exc}") from exc


def load_task(path: str | Path) -> Task:
    """Load a single task from a JSON file.

    Raises ``FileNotFoundError`` when the file is missing and ``ValueError`` when
    the file is not valid JSON or fails validation.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Task file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed task JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Task file {path} must contain a JSON object.")
    return Task.from_dict(data)


def _iter_task_dicts(path: Path):
    """Yield task dicts from a single JSON file, a JSONL file, or a directory."""
    if path.is_dir():
        for child in sorted(path.glob("*.json")):
            yield from _iter_task_dicts(child)
        return
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        for lineno, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("skipping malformed line %d in %s: %s", lineno, path, exc)
                continue
            if isinstance(data, dict):
                yield data
        return
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed task JSON in {path}: {exc}") from exc
    if isinstance(data, dict):
        yield data


def load_tasks(path: str | Path) -> list[Task]:
    """Load tasks from a directory of ``*.json`` files, a ``.jsonl`` file, or a
    single ``.json`` file.

    Malformed JSONL lines are skipped (tolerant replay); a malformed single JSON
    file raises ``ValueError``.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Task path not found: {path}")
    return [Task.from_dict(data) for data in _iter_task_dicts(path)]
