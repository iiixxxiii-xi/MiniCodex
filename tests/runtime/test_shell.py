import sys

from minicodex.runtime.tools.shell import run


def _pycmd(tmp_path, name, body):
    script = tmp_path / name
    script.write_text(body, encoding="utf-8")
    return f"{sys.executable} {script}"


def test_shell_success(tmp_path):
    cmd = _pycmd(tmp_path, "ok.py", "print('hello from shell')\n")
    result = run({"command": cmd}, cwd=tmp_path)
    assert result["returncode"] == 0
    assert result["error"] == ""
    assert "hello from shell" in result["output"]


def test_shell_nonzero_exit(tmp_path):
    cmd = _pycmd(tmp_path, "fail.py", "import sys\nsys.exit(3)\n")
    result = run({"command": cmd}, cwd=tmp_path)
    assert result["returncode"] == 3
    assert result["error"]
    assert result["retryable"] is False


def test_shell_timeout_is_retryable(tmp_path):
    cmd = _pycmd(tmp_path, "slow.py", "import time\ntime.sleep(1)\n")
    result = run({"command": cmd, "timeout": 0.2}, cwd=tmp_path)
    assert result["returncode"] != 0
    assert result["retryable"] is True
    assert "timed out" in result["error"]


def test_shell_missing_command(tmp_path):
    result = run({}, cwd=tmp_path)
    assert result["returncode"] != 0
    assert result["retryable"] is False
