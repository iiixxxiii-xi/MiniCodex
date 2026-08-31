"""CLI: run / eval / report commands work with MockModel (no API key)."""

import json
import sys

from typer.testing import CliRunner

from minicodex.cli.main import app

runner = CliRunner()


def _task_json(task_id: str, *, test_command: str | None = None) -> str:
    cmd = test_command if test_command is not None else f'"{sys.executable}" -c "print(1)"'
    return json.dumps(
        {"id": task_id, "repo": "demo", "instruction": "do it", "test_command": cmd}
    )


def test_help_lists_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("run", "eval", "report"):
        assert command in result.output


def test_run_single_task(tmp_path):
    task_file = tmp_path / "t.json"
    task_file.write_text(_task_json("t1"), encoding="utf-8")
    result = runner.invoke(
        app, ["run", str(task_file), "--mock", "--output-dir", str(tmp_path / "results")]
    )
    assert result.exit_code == 0
    assert "PASS" in result.output
    assert (tmp_path / "results" / "t1" / "trajectory.jsonl").exists()


def test_run_missing_task_errors(tmp_path):
    result = runner.invoke(app, ["run", str(tmp_path / "nope.json"), "--mock"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower() or "missing" in result.output.lower()


def test_eval_runs_ablation_and_writes_report(tmp_path):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "a.json").write_text(_task_json("a"), encoding="utf-8")
    (tasks_dir / "b.json").write_text(_task_json("b"), encoding="utf-8")

    out = tmp_path / "results"
    result = runner.invoke(app, ["eval", str(tasks_dir), "--mock", "--output-dir", str(out)])
    assert result.exit_code == 0
    assert (out / "report.md").exists()
    assert (out / "report.csv").exists()
    assert (out / "minimal.json").exists()
    assert (out / "full.json").exists()


def test_eval_unknown_preset_errors(tmp_path):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "a.json").write_text(_task_json("a"), encoding="utf-8")
    result = runner.invoke(
        app, ["eval", str(tasks_dir), "--mock", "--policies", "bogus", "--output-dir", str(tmp_path / "r")]
    )
    assert result.exit_code == 1


def test_eval_no_tasks_errors(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    result = runner.invoke(app, ["eval", str(empty), "--mock", "--output-dir", str(tmp_path / "r")])
    assert result.exit_code == 1


def test_report_renders(tmp_path):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "a.json").write_text(_task_json("a"), encoding="utf-8")
    out = tmp_path / "results"
    runner.invoke(app, ["eval", str(tasks_dir), "--mock", "--output-dir", str(out)])

    result = runner.invoke(app, ["report", str(out)])
    assert result.exit_code == 0
    assert "Preset" in result.output
    assert "Success Rate" in result.output


def test_report_empty_dir_errors(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    result = runner.invoke(app, ["report", str(empty)])
    assert result.exit_code == 1
