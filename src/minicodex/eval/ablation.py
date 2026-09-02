"""Ablation: run the same task batch under different policy presets.

Each :class:`AblationPreset` toggles loop-level knobs (step budget and requery /
retry bypass). ``run_ablation`` fans the task batch out across every preset and
aggregates per-preset metrics, so the report can show which knob moves which
metric.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic import BaseModel, Field

from minicodex.eval.metrics import BatchMetrics, aggregate_metrics
from minicodex.eval.runner import RunResult, Runner
from minicodex.eval.task import Task


class AblationPreset(BaseModel):
    """A named policy combination to compare.

    Each dimension is independently adjustable, so presets can isolate the
    effect of one knob at a time (context policy, tool policy, retry policy,
    step budget) rather than only the two ``minimal``/``full`` extremes.
    """

    name: str
    step_limit: int = 0
    max_requeries: int = 3
    context_policy: str = "none"
    tool_policy: str = "all"
    retry_policy: str = "fixed"
    description: str = ""


class AblationResult(BaseModel):
    """The outcome of running the full task batch under one preset."""

    preset: str
    results: list[RunResult] = Field(default_factory=list)
    metrics: BatchMetrics = Field(default_factory=BatchMetrics)


DEFAULT_PRESETS: dict[str, AblationPreset] = {
    "minimal": AblationPreset(
        name="minimal",
        step_limit=5,
        max_requeries=0,
        retry_policy="none",
        description="tight step budget, no retry requery",
    ),
    "full": AblationPreset(
        name="full",
        step_limit=0,
        max_requeries=3,
        retry_policy="fixed",
        description="unbounded steps, fixed retry requery",
    ),
    # Single-dimension ablations — each varies exactly one knob against "full".
    "no_retry": AblationPreset(
        name="no_retry",
        step_limit=0,
        max_requeries=3,
        retry_policy="none",
        description="ablate retry: no requery on errors",
    ),
    "backoff": AblationPreset(
        name="backoff",
        step_limit=0,
        max_requeries=3,
        retry_policy="backoff",
        description="ablate retry: exponential backoff requery",
    ),
    "sliding": AblationPreset(
        name="sliding",
        step_limit=0,
        max_requeries=3,
        context_policy="sliding",
        description="ablate context: sliding-window trimming",
    ),
    "truncation": AblationPreset(
        name="truncation",
        step_limit=0,
        max_requeries=3,
        context_policy="truncation",
        description="ablate context: observation truncation",
    ),
    "compaction": AblationPreset(
        name="compaction",
        step_limit=0,
        max_requeries=3,
        context_policy="compaction",
        description="ablate context: summarize-and-offload compaction",
    ),
    "no_test_runner": AblationPreset(
        name="no_test_runner",
        step_limit=0,
        max_requeries=3,
        tool_policy="no_test_runner",
        description="ablate tools: hide the test_runner tool",
    ),
}


async def run_ablation(
    tasks: list[Task],
    model,
    *,
    presets: list[AblationPreset] | None = None,
    output_dir: str | Path | None = None,
    concurrency: int = 4,
) -> list[AblationResult]:
    """Run ``tasks`` under every preset and return one :class:`AblationResult`
    per preset (each carrying per-task results + aggregated metrics).

    Tasks within a preset run concurrently, bounded by a semaphore of size
    ``concurrency`` so a large batch never saturates the model/runtime. The same
    ``model`` is reused across presets; per-run metrics are computed from each
    run's own event log, so reuse does not leak state.
    """
    presets = presets if presets is not None else list(DEFAULT_PRESETS.values())
    semaphore = asyncio.Semaphore(max(1, concurrency))
    results: list[AblationResult] = []
    for preset in presets:
        preset_dir = Path(output_dir) / preset.name if output_dir is not None else None
        runner = Runner(
            model,
            output_dir=preset_dir,
            step_limit=preset.step_limit,
            max_requeries=preset.max_requeries,
            context_policy=preset.context_policy,
            tool_policy=preset.tool_policy,
            retry_policy=preset.retry_policy,
        )
        run_results = await asyncio.gather(
            *(_run_one(runner, task, semaphore) for task in tasks)
        )
        results.append(
            AblationResult(
                preset=preset.name,
                results=run_results,
                metrics=aggregate_metrics([r.metrics for r in run_results]),
            )
        )
    return results


async def _run_one(runner: Runner, task: Task, semaphore: asyncio.Semaphore) -> RunResult:
    """Run a single task, gated by the shared concurrency semaphore."""
    async with semaphore:
        return await runner.run(task)
