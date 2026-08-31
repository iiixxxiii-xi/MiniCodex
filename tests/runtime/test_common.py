import sys

from pydantic import BaseModel

from minicodex.runtime.tools.common import (
    ToolError,
    classify_error,
    failure,
    ok,
    parse_args,
    run_subprocess,
)


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


def test_run_subprocess_decodes_non_ascii_utf8_output(tmp_path):
    # Child writes UTF-8 bytes that are invalid under the Windows GBK codec;
    # run_subprocess must decode them without raising UnicodeDecodeError.
    expected = chr(0x4E2D) + chr(0x6587)
    proc = run_subprocess(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write('\\u4e2d\\u6587'.encode('utf-8'))",
        ],
        cwd=tmp_path,
    )
    assert expected in proc.stdout
