from minicodex.runtime.tools.read_file import run


def test_reads_with_line_numbers(tmp_path):
    (tmp_path / "a.txt").write_text("hello\nworld\n", encoding="utf-8")
    result = run({"path": "a.txt"}, cwd=tmp_path)
    assert result["returncode"] == 0
    assert result["error"] == ""
    assert "1:hello" in result["output"]
    assert "2:world" in result["output"]
    assert result["truncated"] is False


def test_read_file_missing_returns_error(tmp_path):
    result = run({"path": "nope.txt"}, cwd=tmp_path)
    assert result["returncode"] != 0
    assert result["error"]
    assert result["retryable"] is False


def test_read_file_truncates_long_output(tmp_path):
    (tmp_path / "big.txt").write_text("".join(f"line {i}\n" for i in range(1000)), encoding="utf-8")
    result = run({"path": "big.txt", "max_chars": 100}, cwd=tmp_path)
    assert result["truncated"] is True
    assert "line 999" not in result["output"]


def test_read_file_slice_with_start_end(tmp_path):
    (tmp_path / "a.txt").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")
    result = run({"path": "a.txt", "start_line": 2, "end_line": 3}, cwd=tmp_path)
    assert "2:two" in result["output"]
    assert "3:three" in result["output"]
    assert "1:one" not in result["output"]
    assert "4:four" not in result["output"]


def test_read_file_invalid_args(tmp_path):
    result = run({"path": "a.txt", "start_line": "not-an-int"}, cwd=tmp_path)
    assert result["returncode"] != 0
    assert result["error"]
    assert result["retryable"] is False
