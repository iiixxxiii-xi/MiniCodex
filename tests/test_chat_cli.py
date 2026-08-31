"""CLI: the ``chat`` command wires the REPL to a ChatRunner (MockModel, no key)."""

from typer.testing import CliRunner

from minicodex.cli.main import app

runner = CliRunner()


def test_chat_help_lists_command():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "chat" in result.output


def test_chat_missing_repo_errors(tmp_path):
    result = runner.invoke(app, ["chat", "--repo", str(tmp_path / "nope"), "--mock"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_chat_repl_exits_on_quit(tmp_path):
    result = runner.invoke(app, ["chat", "--repo", str(tmp_path), "--mock"], input="quit\n")
    assert result.exit_code == 0


def test_chat_repl_runs_instruction(tmp_path):
    result = runner.invoke(
        app, ["chat", "--repo", str(tmp_path), "--mock"], input="hello\nexit\n"
    )
    assert result.exit_code == 0
    assert "finished" in result.output
