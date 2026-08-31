from minicodex.runtime.tools.write_file import run


def test_writes_file(tmp_path):
    result = run({"path": "a.txt", "content": "hello\nworld"}, cwd=tmp_path)
    assert result["returncode"] == 0
    assert result["error"] == ""
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "hello\nworld"


def test_write_file_creates_parent_dirs(tmp_path):
    run({"path": "x/y/z.txt", "content": "c"}, cwd=tmp_path)
    assert (tmp_path / "x" / "y" / "z.txt").read_text(encoding="utf-8") == "c"


def test_write_file_overwrites_existing(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("old", encoding="utf-8")
    run({"path": "a.txt", "content": "new"}, cwd=tmp_path)
    assert f.read_text(encoding="utf-8") == "new"


def test_write_file_missing_args_returns_error(tmp_path):
    result = run({}, cwd=tmp_path)
    assert result["returncode"] != 0
    assert result["error"]
    assert result["retryable"] is False
