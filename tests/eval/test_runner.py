"""Runner turns a task into a trajectory + metrics + PASS/FAIL verdict."""

import json
import sys

import pytest

from minicodex.eval.metrics import RunMetrics
from minicodex.eval.runner import RunResult, Runner
from minicodex.eval.task import Task
from minicodex.model.mock import MockModel
from minicodex.runtime.local import LocalRuntime
from minicodex.runtime.sandbox.docker import DockerError


def _python_cmd(code: str) -> str:
    return f'"{sys.executable}" -c "{code}"'


def _finishing_model():
    return MockModel(script=[{"tool_calls": []}])


async def test_runner_passes_when_hidden_test_passes(tmp_path):
    task = Task(id="t1", repo="demo", instruction="do it", test_command=_python_cmd("print('ok')"))
    runner = Runner(_finishing_model(), output_dir=tmp_path)
    result = await runner.run(task)
    assert isinstance(result, RunResult)
    assert result.passed is True
    assert result.exit_status == "finished"
    assert result.metrics.task_success is True
    assert result.error == ""


async def test_runner_fails_when_hidden_test_fails(tmp_path):
    task = Task(id="t2", repo="demo", instruction="do it", test_command=_python_cmd("import sys; sys.exit(3)"))
    runner = Runner(_finishing_model(), output_dir=tmp_path)
    result = await runner.run(task)
    assert result.passed is False
    assert result.metrics.task_success is False


async def test_runner_marks_missing_test_command_as_failure(tmp_path):
    task = Task(id="t3", repo="demo", instruction="do it", test_command="")
    runner = Runner(_finishing_model(), output_dir=tmp_path)
    result = await runner.run(task)
    assert result.passed is False
    assert "test_command" in result.error


async def test_runner_computes_metrics_from_trajectory(tmp_path):
    model = MockModel(script=[
        {"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "echo hi"}}]},
        {"tool_calls": []},
    ])
    task = Task(id="t4", repo="demo", instruction="do it", test_command=_python_cmd("print('ok')"))
    runner = Runner(model, output_dir=tmp_path)
    result = await runner.run(task)
    assert result.metrics.tool_calls == 1
    assert result.metrics.avg_tool_calls_per_step == 0.5
    assert result.metrics.total_tokens == 300
    assert result.metrics.total_errors == 0
    assert isinstance(result.metrics, RunMetrics)


async def test_runner_persists_trajectory_and_result(tmp_path):
    task = Task(id="t5", repo="demo", instruction="do it", test_command=_python_cmd("print('ok')"))
    runner = Runner(_finishing_model(), output_dir=tmp_path)
    result = await runner.run(task)

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


async def test_runner_creates_missing_repo_path(tmp_path):
    repo = tmp_path / "new-repo"
    task = Task(
        id="t6", repo="demo", instruction="do it",
        test_command=_python_cmd("print('ok')"), repo_path=str(repo),
    )
    runner = Runner(_finishing_model())
    result = await runner.run(task)
    assert repo.exists()
    assert result.passed is True


async def test_runner_default_model_name_falls_back(tmp_path):
    task = Task(id="t7", repo="demo", instruction="do it", test_command=_python_cmd("print('ok')"))
    runner = Runner(_finishing_model(), output_dir=tmp_path)
    await runner.run(task)
    assert runner.model_name == "MockModel"


def test_runner_hidden_test_decodes_non_ascii_utf8_output(tmp_path):
    # A hidden test emitting UTF-8 bytes invalid under the Windows GBK codec
    # must be read back without raising UnicodeDecodeError.
    expected = chr(0x4E2D) + chr(0x6587)
    code = "import sys; sys.stdout.buffer.write('\\u4e2d\\u6587'.encode('utf-8'))"
    task = Task(id="t8", repo="demo", instruction="do it", test_command=_python_cmd(code))
    runner = Runner(_finishing_model(), output_dir=tmp_path)
    passed, error, output = runner._run_hidden_test(task, tmp_path)
    assert passed is True
    assert error == ""
    assert expected in output


def _write_demo_repo(root) -> None:
    (root / "demo.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (root / "conftest.py").write_text(
        "import os\nimport sys\n\nsys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n",
        encoding="utf-8",
    )
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_demo.py").write_text(
        "import demo\n\n\ndef test_add():\n    assert demo.add(2, 3) == 5\n",
        encoding="utf-8",
    )


def test_runner_uses_fail_to_pass_matrix_over_test_command(tmp_path):
    # A task with a fail_to_pass matrix must be verified via the matrix even
    # when a (bogus) test_command is also present.
    _write_demo_repo(tmp_path)
    task = Task(
        id="t9",
        repo="demo",
        instruction="fix add",
        repo_path=str(tmp_path),
        fail_to_pass=["tests/test_demo.py::test_add"],
        pass_to_pass=[],
        test_command="exit 0",  # would pass, but must be ignored
    )
    runner = Runner(_finishing_model())
    passed, error, _ = runner._run_hidden_test(task, tmp_path)
    assert passed is False
    assert "fail_to_pass" in error


def test_runner_build_runtime_uses_docker_sandbox(tmp_path, monkeypatch):
    calls: dict = {}

    def fake_make_runtime(sandbox, cwd, *, image="python:3.11-slim"):
        calls["sandbox"] = sandbox
        calls["image"] = image
        return LocalRuntime(cwd=cwd)

    monkeypatch.setattr("minicodex.eval.runner.make_runtime", fake_make_runtime)
    runner = Runner(_finishing_model(), sandbox="docker", docker_image="my-image:tag")
    runtime = runner._build_runtime(tmp_path)
    assert isinstance(runtime, LocalRuntime)
    assert calls["sandbox"] == "docker"
    assert calls["image"] == "my-image:tag"


def test_runner_build_runtime_falls_back_on_docker_error(tmp_path, monkeypatch):
    def fake_make_runtime(sandbox, cwd, *, image="python:3.11-slim"):
        raise DockerError("daemon down")

    monkeypatch.setattr("minicodex.eval.runner.make_runtime", fake_make_runtime)
    runner = Runner(_finishing_model(), sandbox="docker")
    runtime = runner._build_runtime(tmp_path)
    assert isinstance(runtime, LocalRuntime)


def test_runner_hidden_test_runs_in_docker_runtime(tmp_path):
    class FakeDocker:
        def __init__(self):
            self.commands = []

        def run_command_sync(self, command, *, timeout=None):
            self.commands.append(command)
            return {"output": "ok", "returncode": 0, "error": ""}

        def run_pytest(self, nodes, *, timeout=120.0):
            return {n: True for n in nodes}

    rt = FakeDocker()
    task = Task(id="t", repo="demo", instruction="x", test_command="pytest -q")
    runner = Runner(_finishing_model())
    passed, error, _ = runner._run_hidden_test(task, tmp_path, rt)
    assert passed is True
    assert error == ""
    assert rt.commands == ["pytest -q"]


def test_runner_matrix_runs_in_docker_runtime(tmp_path):
    class FakeDocker:
        def run_pytest(self, nodes, *, timeout=120.0):
            return {n: (n == "tests/test_demo.py::test_add") for n in nodes}

    rt = FakeDocker()
    task = Task(
        id="t",
        repo="demo",
        instruction="x",
        fail_to_pass=["tests/test_demo.py::test_add"],
        pass_to_pass=["tests/test_demo.py::test_mul"],
    )
    runner = Runner(_finishing_model())
    passed, error, _ = runner._run_hidden_test(task, tmp_path, rt)
    assert passed is False
    assert "pass_to_pass" in error
