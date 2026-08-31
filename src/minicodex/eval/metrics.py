"""Six evaluation metrics extracted from a replayed event log.

The metrics are the closed-loop feedback the harness reports after each run:

1. **Task Success**      — whether the hidden test passed (``SubmissionEvent.passed``).
2. **Avg Tool Calls**    — tool calls per step (``ActionEvent`` / ``StepEvent``).
3. **Token Cost**        — total USD cost (sum of ``ModelCallEvent.cost_usd``).
4. **Latency**           — wall-clock duration (sum of ``StepEvent.duration_ms``).
5. **Recovery Rate**     — fraction of recoverable errors the agent kept going after.
6. **Invalid Tool Call Rate** — ``InvalidToolCallEvent`` / total tool calls.

Every division is guarded: empty logs and missing events produce well-defined
defaults (``0.0`` for rates, ``1.0`` for recovery when nothing needed recovery).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from minicodex.core.events import (
    ActionEvent,
    ErrorEvent,
    Event,
    InvalidToolCallEvent,
    ModelCallEvent,
    StepEvent,
    SubmissionEvent,
)


class RunMetrics(BaseModel):
    """Per-run metrics derived from a single trajectory's event log."""

    task_success: bool = False
    tool_calls: int = 0
    avg_tool_calls_per_step: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    total_errors: int = 0
    recoverable_errors: int = 0
    recovered_errors: int = 0
    recovery_rate: float = 1.0
    invalid_tool_calls: int = 0
    invalid_tool_call_rate: float = 0.0


class BatchMetrics(BaseModel):
    """Aggregate metrics over a set of runs (used in ablation comparisons)."""

    n_tasks: int = 0
    success_rate: float = 0.0
    avg_tool_calls: float = 0.0
    avg_cost_usd: float = 0.0
    avg_latency_ms: float = 0.0
    avg_recovery_rate: float = 0.0
    avg_invalid_tool_call_rate: float = 0.0


def compute_metrics(events: list[Event]) -> RunMetrics:
    """Compute the six metrics from an ordered event list (the trajectory)."""
    model_calls = [e for e in events if isinstance(e, ModelCallEvent)]
    steps = [e for e in events if isinstance(e, StepEvent)]
    actions = [e for e in events if isinstance(e, ActionEvent)]
    errors = [e for e in events if isinstance(e, ErrorEvent)]
    invalid = [e for e in events if isinstance(e, InvalidToolCallEvent)]
    submission = next((e for e in reversed(events) if isinstance(e, SubmissionEvent)), None)

    tool_calls = len(actions)
    n_steps = len(steps)
    avg_tool_calls = tool_calls / n_steps if n_steps else 0.0

    input_tokens = sum(e.input_tokens for e in model_calls)
    output_tokens = sum(e.output_tokens for e in model_calls)
    cost_usd = sum(e.cost_usd for e in model_calls)

    if steps:
        latency_ms = sum(e.duration_ms for e in steps)
    else:
        timestamps = [e.timestamp for e in events]
        latency_ms = (max(timestamps) - min(timestamps)) * 1000 if timestamps else 0.0

    recoverable_errors = sum(1 for e in errors if e.recoverable)
    # An error is "recovered" when the agent kept going after it — i.e. a later
    # model call or step exists in the log.
    continued_indices = [
        i for i, e in enumerate(events) if isinstance(e, (ModelCallEvent, StepEvent))
    ]
    max_continued = max(continued_indices) if continued_indices else -1
    recovered_errors = sum(
        1
        for i, e in enumerate(events)
        if isinstance(e, ErrorEvent) and e.recoverable and i < max_continued
    )
    recovery_rate = recovered_errors / recoverable_errors if recoverable_errors else 1.0

    invalid_tool_calls = len(invalid)
    invalid_denominator = invalid_tool_calls + tool_calls
    invalid_tool_call_rate = invalid_tool_calls / invalid_denominator if invalid_denominator else 0.0

    return RunMetrics(
        task_success=bool(submission and submission.passed),
        tool_calls=tool_calls,
        avg_tool_calls_per_step=avg_tool_calls,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        total_errors=len(errors),
        recoverable_errors=recoverable_errors,
        recovered_errors=recovered_errors,
        recovery_rate=recovery_rate,
        invalid_tool_calls=invalid_tool_calls,
        invalid_tool_call_rate=invalid_tool_call_rate,
    )


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def aggregate_metrics(metrics: list[RunMetrics]) -> BatchMetrics:
    """Average per-run metrics into a single batch summary."""
    if not metrics:
        return BatchMetrics()
    return BatchMetrics(
        n_tasks=len(metrics),
        success_rate=_mean([1.0 if m.task_success else 0.0 for m in metrics]),
        avg_tool_calls=_mean([float(m.tool_calls) for m in metrics]),
        avg_cost_usd=_mean([m.cost_usd for m in metrics]),
        avg_latency_ms=_mean([m.latency_ms for m in metrics]),
        avg_recovery_rate=_mean([m.recovery_rate for m in metrics]),
        avg_invalid_tool_call_rate=_mean([m.invalid_tool_call_rate for m in metrics]),
    )
