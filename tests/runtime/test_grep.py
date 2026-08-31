from minicodex.runtime.tools.grep import run


def test_grep_matches_in_file(tmp_path):
    (tmp_path / "a.txt").write_text("hello world\nneedle here\nother\n", encoding="utf-8")
    result = run({"pattern": "needle", "path": "a.txt"}, cwd=tmp_path)
    assert result["returncode"] == 0
    assert result["matches"] == 1
    assert "a.txt:2:needle here" in result["output"]


def test_grep_recursive_directory(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("x\nneedle\n", encoding="utf-8")
    result = run({"pattern": "needle", "path": "."}, cwd=tmp_path)
    assert result["matches"] == 1
    assert "needle" in result["output"]


def test_grep_no_match(tmp_path):
    (tmp_path / "a.txt").write_text("hello\n", encoding="utf-8")
    result = run({"pattern": "zzz", "path": "."}, cwd=tmp_path)
    assert result["matches"] == 0
    assert result["output"] == ""


def test_grep_case_insensitive(tmp_path):
    (tmp_path / "a.txt").write_text("HELLO\n", encoding="utf-8")
    result = run({"pattern": "hello", "path": ".", "case_sensitive": False}, cwd=tmp_path)
    assert result["matches"] == 1


def test_grep_max_results(tmp_path):
    (tmp_path / "a.txt").write_text("".join("match\n" for _ in range(10)), encoding="utf-8")
    result = run({"pattern": "match", "path": ".", "max_results": 3}, cwd=tmp_path)
    assert result["matches"] == 3


def test_grep_missing_path_returns_error(tmp_path):
    result = run({"pattern": "x", "path": "nope"}, cwd=tmp_path)
    assert result["returncode"] != 0
    assert result["retryable"] is False


def test_grep_invalid_regex_returns_error(tmp_path):
    result = run({"pattern": "(", "path": "."}, cwd=tmp_path)
    assert result["returncode"] != 0
    assert result["retryable"] is False
