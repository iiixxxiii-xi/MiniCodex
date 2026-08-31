"""Six metrics are extracted deterministically from an event log."""

import pytest

from minicodex.core.events import (
    ActionEvent,
    ErrorEvent,
    EventSource,
    InvalidToolCallEvent,
    ModelCallEvent,
    ObservationEvent,
    StepEvent,
    SubmissionEvent,
)
from minicodex.eval.metrics import BatchMetrics, RunMetrics, aggregate_metrics, compute_metrics


def _trajectory():
    return [
        ModelCallEvent(
            source=EventSource.MODEL, model="mock", input_tokens=100, output_tokens=50, cost_usd=0.001
        ),
        StepEvent(source=EventSource.CONTROLLER, step_index=0, duration_ms=10.0),
        ActionEvent(source=EventSource.AGENT, tool_name="shell", tool_call_id="c1", action={"command": "ls"}),
        ObservationEvent(
            source=EventSource.RUNTIME, tool_name="shell", tool_call_id="c1", action_id="a1",
            observation={"output": "x"},
        ),
        InvalidToolCallEvent(source=EventSource.CONTROLLER, tool_name="", reason="empty name"),
        ErrorEvent(source=EventSource.CONTROLLER, error_type="FormatError", recoverable=True, message="bad"),
        ModelCallEvent(
            source=EventSource.MODEL, model="mock", input_tokens=100, output_tokens=50, cost_usd=0.002
        ),
        StepEvent(source=EventSource.CONTROLLER, step_index=1, duration_ms=20.0),
        SubmissionEvent(source=EventSource.CONTROLLER, content="patch", passed=True),
    ]


def test_compute_metrics_exact_values():
    m = compute_metrics(_trajectory())

    # Task Success
    assert m.task_success is True
    # Average tool calls per step
    assert m.tool_calls == 1
    assert m.avg_tool_calls_per_step == 0.5
    # Token cost
    assert m.input_tokens == 200
    assert m.output_tokens == 100
    assert m.total_tokens == 300
    assert m.cost_usd == 0.003
    # Latency (sum of step durations)
    assert m.latency_ms == 30.0
    # Recovery rate
    assert m.total_errors == 1
    assert m.recoverable_errors == 1
    assert m.recovered_errors == 1
    assert m.recovery_rate == 1.0
    # Invalid tool call rate
    assert m.invalid_tool_calls == 1
    assert m.invalid_tool_call_rate == 0.5


def test_empty_events_yield_safe_defaults():
    m = compute_metrics([])
    assert m.task_success is False
    assert m.tool_calls == 0
    assert m.avg_tool_calls_per_step == 0.0
    assert m.total_tokens == 0
    assert m.cost_usd == 0.0
    assert m.latency_ms == 0.0
    assert m.total_errors == 0
    assert m.recovery_rate == 1.0
    assert m.invalid_tool_call_rate == 0.0


def test_success_is_false_without_submission_event():
    m = compute_metrics([ModelCallEvent(source=EventSource.MODEL, model="m")])
    assert m.task_success is False


def test_recovery_rate_zero_when_recoverable_error_not_followed():
    events = [
        ModelCallEvent(source=EventSource.MODEL, model="m", input_tokens=1, output_tokens=1),
        ErrorEvent(source=EventSource.CONTROLLER, error_type="FormatError", recoverable=True),
    ]
    m = compute_metrics(events)
    assert m.recoverable_errors == 1
    assert m.recovered_errors == 0
    assert m.recovery_rate == 0.0


def test_recovery_rate_one_when_no_recoverable_errors():
    events = [
        ModelCallEvent(source=EventSource.MODEL, model="m"),
        ErrorEvent(source=EventSource.CONTROLLER, error_type="Error", recoverable=False),
    ]
    m = compute_metrics(events)
    assert m.recovery_rate == 1.0


def test_invalid_rate_zero_when_no_tool_calls():
    m = compute_metrics([StepEvent(source=EventSource.CONTROLLER, step_index=0, duration_ms=1.0)])
    assert m.invalid_tool_call_rate == 0.0


def test_latency_falls_back_to_timestamp_span():
    first = ModelCallEvent(source=EventSource.MODEL, model="m", input_tokens=1, output_tokens=1)
    second = ModelCallEvent(source=EventSource.MODEL, model="m", input_tokens=1, output_tokens=1)
    first.timestamp = 100.0
    second.timestamp = 100.5
    m = compute_metrics([first, second])
    assert m.latency_ms == 500.0


def test_aggregate_metrics_averages():
    a = RunMetrics(
        task_success=True, tool_calls=4, avg_tool_calls_per_step=1.0, cost_usd=1.0,
        latency_ms=100.0, recovery_rate=1.0, invalid_tool_call_rate=0.1,
    )
    b = RunMetrics(
        task_success=False, tool_calls=2, avg_tool_calls_per_step=0.5, cost_usd=0.5,
        latency_ms=50.0, recovery_rate=0.5, invalid_tool_call_rate=0.2,
    )
    agg = aggregate_metrics([a, b])
    assert isinstance(agg, BatchMetrics)
    assert agg.n_tasks == 2
    assert agg.success_rate == 0.5
    assert agg.avg_tool_calls == 3.0
    assert agg.avg_cost_usd == 0.75
    assert agg.avg_latency_ms == 75.0
    assert agg.avg_recovery_rate == 0.75
    assert agg.avg_invalid_tool_call_rate == pytest.approx(0.15)


def test_aggregate_empty_is_safe():
    agg = aggregate_metrics([])
    assert agg.n_tasks == 0
    assert agg.success_rate == 0.0
    assert agg.avg_tool_calls == 0.0
