import sys

from minicodex.runtime.tools.test_runner import RunnerArgs, run


def _pycmd(tmp_path, name, body):
    script = tmp_path / name
    script.write_text(body, encoding="utf-8")
    return f"{sys.executable} {script}"


def test_default_command_is_pytest():
    assert RunnerArgs().command == "pytest -q"


def test_test_runner_success(tmp_path):
    cmd = _pycmd(tmp_path, "pass.py", "print('2 passed')\n")
    result = run({"command": cmd}, cwd=tmp_path)
    assert result["returncode"] == 0
    assert result["error"] == ""
    assert "2 passed" in result["output"]


def test_test_runner_failure(tmp_path):
    cmd = _pycmd(tmp_path, "fail.py", "import sys\nsys.exit(1)\n")
    result = run({"command": cmd}, cwd=tmp_path)
    assert result["returncode"] != 0
    assert result["error"]
    assert result["retryable"] is False


def test_test_runner_timeout_is_retryable(tmp_path):
    cmd = _pycmd(tmp_path, "slow.py", "import time\ntime.sleep(1)\n")
    result = run({"command": cmd, "timeout": 0.2}, cwd=tmp_path)
    assert result["retryable"] is True
    assert "timed out" in result["error"]


def test_test_runner_reads_non_ascii_utf8_output(tmp_path):
    # Subprocess emits UTF-8 bytes that are invalid under the Windows GBK codec;
    # decoding must not raise UnicodeDecodeError and must round-trip the text.
    # Use chr()/escapes so the test source stays pure ASCII (immune to any
    # locale/terminal source-encoding mangling on Windows).
    expected = chr(0x4E2D) + chr(0x6587) + " " + chr(0xB7) + " " + chr(0xE9)
    body = (
        "import sys\n"
        "sys.stdout.buffer.write('\\u4e2d\\u6587 \\u00b7 \\u00e9\\n'.encode('utf-8'))\n"
    )
    cmd = _pycmd(tmp_path, "unicode.py", body)
    result = run({"command": cmd}, cwd=tmp_path)
    assert result["returncode"] == 0
    assert result["error"] == ""
    assert expected in result["output"]
