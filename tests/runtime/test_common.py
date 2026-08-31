from pydantic import BaseModel

from minicodex.runtime.tools.common import ToolError, classify_error, failure, ok, parse_args


def test_ok_shape():
    r = ok("hi", extra=1)
    assert r["output"] == "hi"
    assert r["returncode"] == 0
    assert r["error"] == ""
    assert r["extra"] == 1


def test_failure_shape():
    r = failure("boom", retryable=True)
    assert r["error"] == "boom"
    assert r["returncode"] == 1
    assert r["retryable"] is True


def test_failure_defaults_not_retryable():
    r = failure("boom")
    assert r["retryable"] is False


def test_classify_timeout_retryable():
    assert classify_error(TimeoutError()) is True
    assert classify_error(FileNotFoundError()) is False
    assert classify_error(ValueError()) is False


class Args(BaseModel):
    x: int


def test_parse_args_valid():
    assert parse_args(Args, {"x": 1}).x == 1


def test_parse_args_invalid_raises_toolerror():
    try:
        parse_args(Args, {})
    except ToolError as exc:
        assert exc.retryable is False
        assert "Invalid arguments" in exc.message
    else:
        raise AssertionError("expected ToolError")
