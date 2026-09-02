"""Failure collection: bucket failed run trajectories by failure reason.

``collect_failures`` walks a list of :class:`~minicodex.eval.runner.RunResult`
and groups every *failed* run by why it failed — the loop's ``exit_status``
(``ModelError`` / ``LimitsExceeded`` / ``RepeatedFormatError`` / ``Error``), or
a derived ``timeout`` / ``TestFailed`` reason when the loop finished but the
hidden test did not pass. Each category reports its count plus the replayable
trajectory paths (the persisted ``trajectory.jsonl`` files), so failures can be
replayed and inspected after the fact.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from minicodex.eval.runner import RunResult


class FailureCategory(BaseModel):
    """One failure reason and the replayable trajectories that hit it."""

    exit_status: str
    count: int = 0
    trajectory_paths: list[str] = Field(default_factory=list)


class FailureCollection(BaseModel):
    """All failure categories produced by a batch, plus the total failure count."""

    total_failures: int = 0
    categories: list[FailureCategory] = Field(default_factory=list)


def _classify(result: RunResult) -> str:
    """Return the failure reason for a failed ``RunResult``."""
    status = (result.exit_status or "").strip()
    if status and status != "finished":
        return status
    if "timed out" in (result.error or "").lower():
        return "timeout"
    return "TestFailed"


def collect_failures(results: list[RunResult]) -> FailureCollection:
    """Group failed runs by failure reason, returning counts and replayable paths.

    Passed runs are ignored. Runs the loop could not finish are bucketed by their
    ``exit_status``; runs that finished but failed the hidden test are bucketed as
    ``timeout`` (when the test timed out) or ``TestFailed`` otherwise.
    """
    buckets: dict[str, list[str | None]] = {}
    for result in results:
        if result.passed:
            continue
        reason = _classify(result)
        buckets.setdefault(reason, []).append(result.trajectory_path)

    categories = [
        FailureCategory(
            exit_status=reason,
            count=len(paths),
            trajectory_paths=[p for p in paths if p],
        )
        for reason, paths in sorted(buckets.items())
    ]
    return FailureCollection(
        total_failures=sum(len(paths) for paths in buckets.values()),
        categories=categories,
    )
