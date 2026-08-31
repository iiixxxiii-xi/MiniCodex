"""Runner turns a task into a trajectory + metrics + PASS/FAIL verdict."""

import json
import sys

import pytest

from minicodex.eval.metrics import RunMetrics
from minicodex.eval.runner import RunResult, Runner
from minicodex.eval.task import Task
from minicodex.model.mock import MockModel


def _python_cmd(code: str) -> str:
    return f'"{sys.executable}" -c "{code}"'


def _finishing_model():
    return MockModel(script=[{"tool_calls": []}])


def test_runner_passes_when_hidden_test_passes(tmp_path):
    task = Task(id="t1", repo="demo", instruction="do it", test_command=_python_cmd("print('ok')"))
    runner = Runner(_finishing_model(), output_dir=tmp_path)
    result = runner.run(task)
    assert isinstance(result, RunResult)
    assert result.passed is True
    assert result.exit_status == "finished"
    assert result.metrics.task_success is True
    assert result.error == ""


def test_runner_fails_when_hidden_test_fails(tmp_path):
    task = Task(id="t2", repo="demo", instruction="do it", test_command=_python_cmd("import sys; sys.exit(3)"))
    runner = Runner(_finishing_model(), output_dir=tmp_path)
    result = runner.run(task)
    assert result.passed is False
    assert result.metrics.task_success is False


def test_runner_marks_missing_test_command_as_failure(tmp_path):
    task = Task(id="t3", repo="demo", instruction="do it", test_command="")
    runner = Runner(_finishing_model(), output_dir=tmp_path)
    result = runner.run(task)
    assert result.passed is False
    assert "test_command" in result.error


def test_runner_computes_metrics_from_trajectory(tmp_path):
    model = MockModel(script=[
        {"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "echo hi"}}]},
        {"tool_calls": []},
    ])
    task = Task(id="t4", repo="demo", instruction="do it", test_command=_python_cmd("print('ok')"))
    runner = Runner(model, output_dir=tmp_path)
    result = runner.run(task)
    assert result.metrics.tool_calls == 1
    assert result.metrics.avg_tool_calls_per_step == 0.5
    assert result.metrics.total_tokens == 300
    assert result.metrics.total_errors == 0
    assert isinstance(result.metrics, RunMetrics)


def test_runner_persists_trajectory_and_result(tmp_path):
    task = Task(id="t5", repo="demo", instruction="do it", test_command=_python_cmd("print('ok')"))
    runner = Runner(_finishing_model(), output_dir=tmp_path)
    result = runner.run(task)

    traj_path = tmp_path / "t5" / "trajectory.jsonl"
    result_path = tmp_path / "t5" / "result.json"
    assert traj_path.exists()
    assert result_path.exists()
    lines = [json.loads(line) for line in traj_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    kinds = {line["kind"] for line in lines}
    assert "model_call" in kinds
    assert "step" in kinds
    assert "submission" in kinds
    saved = json.loads(result_path.read_text(encoding="utf-8"))
    assert saved["task_id"] == "t5"
    assert saved["passed"] is True


def test_runner_creates_missing_repo_path(tmp_path):
    repo = tmp_path / "new-repo"
    task = Task(
        id="t6", repo="demo", instruction="do it",
        test_command=_python_cmd("print('ok')"), repo_path=str(repo),
    )
    runner = Runner(_finishing_model())
    result = runner.run(task)
    assert repo.exists()
    assert result.passed is True


def test_runner_default_model_name_falls_back(tmp_path):
    task = Task(id="t7", repo="demo", instruction="do it", test_command=_python_cmd("print('ok')"))
    runner = Runner(_finishing_model(), output_dir=tmp_path)
    runner.run(task)
    assert runner.model_name == "MockModel"
