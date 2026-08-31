"""Ablation: run the same task batch under different policy presets.

Each :class:`AblationPreset` toggles loop-level knobs (step budget and requery /
retry bypass). ``run_ablation`` fans the task batch out across every preset and
aggregates per-preset metrics, so the report can show which knob moves which
metric.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from minicodex.eval.metrics import BatchMetrics, aggregate_metrics
from minicodex.eval.runner import RunResult, Runner
from minicodex.eval.task import Task


class AblationPreset(BaseModel):
    """A named policy combination to compare."""

    name: str
    step_limit: int = 0
    max_requeries: int = 3
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
        description="tight step budget, no retry requery",
    ),
    "full": AblationPreset(
        name="full",
        step_limit=0,
        max_requeries=3,
        description="unbounded steps, retry requery enabled",
    ),
}


def run_ablation(
    tasks: list[Task],
    model,
    *,
    presets: list[AblationPreset] | None = None,
    output_dir: str | Path | None = None,
) -> list[AblationResult]:
    """Run ``tasks`` under every preset and return one :class:`AblationResult`
    per preset (each carrying per-task results + aggregated metrics).

    The same ``model`` is reused across presets; per-run metrics are computed
    from each run's own event log, so reuse does not leak state.
    """
    presets = presets if presets is not None else list(DEFAULT_PRESETS.values())
    results: list[AblationResult] = []
    for preset in presets:
        preset_dir = Path(output_dir) / preset.name if output_dir is not None else None
        runner = Runner(
            model,
            output_dir=preset_dir,
            step_limit=preset.step_limit,
            max_requeries=preset.max_requeries,
        )
        run_results = [runner.run(task) for task in tasks]
        results.append(
            AblationResult(
                preset=preset.name,
                results=run_results,
                metrics=aggregate_metrics([r.metrics for r in run_results]),
            )
        )
    return results
