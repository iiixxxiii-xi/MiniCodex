"""Incremental checkpointing for crash recovery.

After every step the loop serializes (messages + counters + executed actions)
to disk. On restart, :meth:`CheckpointManager.load` recovers the latest valid
checkpoint, skipping any file that was torn by a crash mid-write.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

_FILENAME_RE = re.compile(r"checkpoint-(\d+)\.json$")


class CheckpointData(BaseModel):
    """The serialized state captured at a single step."""

    version: int = 1
    step: int = 0
    messages: list[dict] = Field(default_factory=list)
    counters: dict[str, float] = Field(default_factory=dict)
    executed_actions: list[dict] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


class CheckpointManager:
    """Write and recover step checkpoints under a directory.

    Each checkpoint is written atomically (temp file then ``os.replace``) so a
    crash can never leave a half-written checkpoint that is mistaken for a valid
    one. Files are named ``checkpoint-<step:06d>.json``; recovery picks the
    highest step that parses cleanly.
    """

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def save(self, state: CheckpointData) -> Path:
        """Atomically persist ``state`` and return the checkpoint path."""
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self.directory / f"checkpoint-{state.step:06d}.json"
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp, target)
        return target

    def load(self) -> CheckpointData | None:
        """Recover the latest valid checkpoint, or ``None`` if none exists.

        Candidates are tried newest-first; a file that fails to parse (torn
        write, corrupt JSON, invalid fields) is skipped with a warning and the
        next-newest is tried.
        """
        for path in self._candidates():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return CheckpointData.model_validate(data)
            except (OSError, json.JSONDecodeError, ValidationError) as exc:
                logger.warning("skipping corrupt checkpoint %s: %s", path, exc)
        return None

    def _candidates(self) -> list[Path]:
        """Checkpoint files sorted by step number, newest first."""
        if not self.directory.exists():
            return []
        indexed: list[tuple[int, Path]] = []
        for path in self.directory.glob("checkpoint-*.json"):
            match = _FILENAME_RE.match(path.name)
            if match:
                indexed.append((int(match.group(1)), path))
        indexed.sort(key=lambda item: item[0], reverse=True)
        return [path for _, path in indexed]
