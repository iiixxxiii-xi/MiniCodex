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
    for command in ("run", "eval", "report", "chat"):
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


def test_run_help_shows_mcp_option():
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "--mcp" in result.output


def test_run_with_mcp_degrades_gracefully(tmp_path):
    # An unreachable MCP server must not crash the run: the agent simply runs
    # without the external tools.
    task_file = tmp_path / "t.json"
    task_file.write_text(_task_json("t1"), encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "run",
            str(task_file),
            "--mock",
            "--mcp",
            "definitely-not-a-real-command-xyz",
            "--output-dir",
            str(tmp_path / "results"),
        ],
    )
    assert result.exit_code == 0
    assert "PASS" in result.output


def test_run_sandbox_docker_selects_docker_runtime(tmp_path, monkeypatch):
    # --sandbox docker must route through the docker runtime factory without
    # actually starting a container (the factory is faked).
    import importlib

    from minicodex.runtime.local import builtin_runtime

    cli_main = importlib.import_module("minicodex.cli.main")
    calls: dict = {}

    def fake_make_runtime(sandbox, cwd, *, image="python:3.11-slim"):
        calls["sandbox"] = sandbox
        calls["image"] = image
        return builtin_runtime(cwd=cwd)

    monkeypatch.setattr(cli_main, "docker_available", lambda: True)
    monkeypatch.setattr("minicodex.eval.runner.make_runtime", fake_make_runtime)

    task_file = tmp_path / "t.json"
    task_file.write_text(_task_json("t1"), encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "run",
            str(task_file),
            "--mock",
            "--sandbox",
            "docker",
            "--output-dir",
            str(tmp_path / "results"),
        ],
    )
    assert result.exit_code == 0
    assert calls.get("sandbox") == "docker"
    assert "PASS" in result.output


def test_run_sandbox_docker_falls_back_to_local_when_daemon_down(tmp_path, monkeypatch):
    import importlib

    cli_main = importlib.import_module("minicodex.cli.main")
    monkeypatch.setattr(cli_main, "docker_available", lambda: False)
    task_file = tmp_path / "t.json"
    task_file.write_text(_task_json("t1"), encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "run",
            str(task_file),
            "--mock",
            "--sandbox",
            "docker",
            "--output-dir",
            str(tmp_path / "results"),
        ],
    )
    assert result.exit_code == 0
    assert "PASS" in result.output
    assert "local" in result.output  # warning hints at the local fallback


def test_run_sandbox_invalid_value_errors(tmp_path):
    task_file = tmp_path / "t.json"
    task_file.write_text(_task_json("t1"), encoding="utf-8")
    result = runner.invoke(app, ["run", str(task_file), "--mock", "--sandbox", "bogus"])
    assert result.exit_code != 0
