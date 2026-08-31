import subprocess

from minicodex.runtime.tools.git import run


def _init_repo(tmp_path):
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "t@example.com"],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "T"],
        check=True, capture_output=True, text=True,
    )
    (tmp_path / "a.txt").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "a.txt"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True, capture_output=True, text=True)


def test_git_status(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "b.txt").write_text("new\n", encoding="utf-8")
    result = run({"args": ["status", "--porcelain"]}, cwd=tmp_path)
    assert result["returncode"] == 0
    assert result["error"] == ""
    assert "b.txt" in result["output"]


def test_git_diff(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "a.txt").write_text("world\n", encoding="utf-8")
    result = run({"args": ["diff"]}, cwd=tmp_path)
    assert result["returncode"] == 0
    assert "world" in result["output"]


def test_git_invalid_command(tmp_path):
    _init_repo(tmp_path)
    result = run({"args": ["not-a-git-command"]}, cwd=tmp_path)
    assert result["returncode"] != 0
    assert result["error"]
    assert result["retryable"] is False


def test_git_missing_args(tmp_path):
    result = run({}, cwd=tmp_path)
    assert result["returncode"] != 0
    assert result["retryable"] is False
