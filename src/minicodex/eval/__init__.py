"""Evaluation: metrics, tasks, runner, SWE-bench parsing, ablation, and reporting."""

from minicodex.eval.ablation import (
    AblationPreset,
    AblationResult,
    DEFAULT_PRESETS,
    run_ablation,
)
from minicodex.eval.metrics import (
    BatchMetrics,
    RunMetrics,
    aggregate_metrics,
    compute_metrics,
)
from minicodex.eval.report import (
    dump_ablation_results,
    load_ablation_results,
    render_csv,
    render_markdown,
    write_report,
)
from minicodex.eval.runner import RunResult, Runner
from minicodex.eval.swebench import parse_swebench_jsonl, to_task
from minicodex.eval.task import Task, load_task, load_tasks

__all__ = [
    "Task",
    "load_task",
    "load_tasks",
    "RunResult",
    "Runner",
    "RunMetrics",
    "BatchMetrics",
    "compute_metrics",
    "aggregate_metrics",
    "parse_swebench_jsonl",
    "to_task",
    "AblationPreset",
    "AblationResult",
    "DEFAULT_PRESETS",
    "run_ablation",
    "render_markdown",
    "render_csv",
    "write_report",
    "dump_ablation_results",
    "load_ablation_results",
]
