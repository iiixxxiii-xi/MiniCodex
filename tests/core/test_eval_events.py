from minicodex.core.events import (
    ErrorEvent,
    EventSource,
    InvalidToolCallEvent,
    ModelCallEvent,
    StepEvent,
    SubmissionEvent,
)


def test_model_call_event_carries_usage():
    e = ModelCallEvent(
        source=EventSource.MODEL,
        model="claude-sonnet-4-5",
        input_tokens=120,
        output_tokens=45,
        cost_usd=0.001,
    )
    assert e.kind == "model_call"
    assert e.input_tokens == 120
    assert e.output_tokens == 45
    assert e.cost_usd == 0.001


def test_step_event_carries_duration():
    e = StepEvent(source=EventSource.CONTROLLER, step_index=3, duration_ms=12.5)
    assert e.kind == "step"
    assert e.step_index == 3
    assert e.duration_ms == 12.5


def test_invalid_tool_call_event():
    e = InvalidToolCallEvent(source=EventSource.CONTROLLER, tool_name="", reason="empty tool name")
    assert e.kind == "invalid_tool_call"
    assert e.reason == "empty tool name"


def test_error_event_recoverable():
    e = ErrorEvent(
        source=EventSource.CONTROLLER,
        error_type="FormatError",
        recoverable=True,
        message="bad",
    )
    assert e.kind == "error"
    assert e.recoverable is True


def test_submission_event():
    e = SubmissionEvent(source=EventSource.CONTROLLER, content="diff --git", passed=True)
    assert e.kind == "submission"
    assert e.passed is True
