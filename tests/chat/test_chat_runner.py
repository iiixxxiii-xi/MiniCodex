"""ChatRunner: turn a natural-language instruction into a repo edit + git diff."""

import subprocess

import pytest

from minicodex.chat.runner import ChatRunner, ChatTurn, run_chat_session
from minicodex.model.base import ModelError
from minicodex.model.mock import MockModel


def _git(*args, cwd):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True)


def _make_git_repo(root) -> str:
    """Create a git repo with one tracked file, returning the repo path."""
    _git("init", "-q", cwd=root)
    (root / "mean.py").write_text(
        "def mean(xs):\n    return sum(xs) / len(xs)\n", encoding="utf-8"
    )
    _git("add", "mean.py", cwd=root)
    _git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "init", cwd=root)
    return str(root)


def _finishing_model():
    return MockModel(script=[{"tool_calls": []}])


class _FailingModel:
    def query(self, messages, tools):
        raise ModelError("boom")

    def stream(self, messages, tools):
        raise ModelError("boom")

    def cancel(self):
        pass


def test_chat_runner_edits_file_and_returns_diff(tmp_path):
    repo = _make_git_repo(tmp_path)
    model = MockModel(script=[
        {
            "tool_calls": [
                {
                    "id": "1",
                    "name": "write_file",
                    "arguments": {
                        "path": "mean.py",
                        "content": "def mean(xs):\n    if not xs:\n        return 0\n    return sum(xs) / len(xs)\n",
                    },
                }
            ]
        },
        {"tool_calls": []},
    ])
    runner = ChatRunner(model, repo)

    turn = runner.run("make mean return 0 for empty input")

    assert isinstance(turn, ChatTurn)
    assert turn.exit_status == "finished"
    assert "write_file" in turn.tool_calls
    assert "return 0" in turn.diff
    assert turn.error == ""


def test_chat_runner_no_diff_when_no_changes(tmp_path):
    _make_git_repo(tmp_path)
    runner = ChatRunner(_finishing_model(), tmp_path)

    turn = runner.run("do nothing")

    assert turn.exit_status == "finished"
    assert turn.diff == ""
    assert turn.tool_calls == []


def test_chat_runner_captures_tool_call_order(tmp_path):
    model = MockModel(script=[
        {"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "echo hi"}}]},
        {"tool_calls": [{"id": "2", "name": "grep", "arguments": {"pattern": "x", "path": "."}}]},
        {"tool_calls": []},
    ])
    runner = ChatRunner(model, tmp_path)

    turn = runner.run("inspect")

    assert turn.tool_calls == ["shell", "grep"]


def test_chat_runner_hits_step_limit(tmp_path):
    model = MockModel(
        script=[{"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "ls"}}]}]
    )
    runner = ChatRunner(model, tmp_path, step_limit=2)

    turn = runner.run("loop forever")

    assert turn.exit_status == "LimitsExceeded"


def test_chat_runner_degrades_on_model_error(tmp_path):
    runner = ChatRunner(_FailingModel(), tmp_path, max_requeries=1)

    turn = runner.run("anything")

    assert turn.exit_status == "ModelError"
    assert turn.diff == ""


def test_chat_runner_summary_mentions_exit_status(tmp_path):
    _make_git_repo(tmp_path)
    runner = ChatRunner(_finishing_model(), tmp_path)

    turn = runner.run("hello")

    assert "finished" in turn.summary


def test_chat_runner_rejects_missing_repo(tmp_path):
    with pytest.raises(ValueError):
        ChatRunner(_finishing_model(), tmp_path / "does-not-exist")


def test_session_exits_on_quit(tmp_path):
    runner = ChatRunner(_finishing_model(), tmp_path)
    lines = iter(["quit"])
    output = []
    rc = run_chat_session(runner, readline=lambda: next(lines), write=output.append)
    assert rc == 0
    assert output == []


def test_session_exits_on_empty_input(tmp_path):
    runner = ChatRunner(_finishing_model(), tmp_path)
    lines = iter(["   "])
    rc = run_chat_session(runner, readline=lambda: next(lines), write=lambda s: None)
    assert rc == 0


def test_session_exits_on_ctrl_c(tmp_path):
    runner = ChatRunner(_finishing_model(), tmp_path)

    def readline():
        raise KeyboardInterrupt

    rc = run_chat_session(runner, readline=readline, write=lambda s: None)
    assert rc == 0


def test_session_runs_instruction_and_renders(tmp_path):
    _make_git_repo(tmp_path)
    runner = ChatRunner(_finishing_model(), tmp_path)
    lines = iter(["say hello", "exit"])
    output = []

    rc = run_chat_session(runner, readline=lambda: next(lines), write=output.append)

    assert rc == 0
    assert any("finished" in line for line in output)
