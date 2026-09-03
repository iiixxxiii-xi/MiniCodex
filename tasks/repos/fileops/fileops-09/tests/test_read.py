from fileops.read import count_lines, read_lines, tail


def test_read_lines_basic(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\nb\nc\n", encoding="utf-8")
    assert read_lines(path) == ["a", "b", "c"]


def test_read_lines_no_trailing_newline(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\nb", encoding="utf-8")
    assert read_lines(path) == ["a", "b"]


def test_read_lines_preserves_trailing_spaces(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("hello   \nworld\n", encoding="utf-8")
    assert read_lines(path) == ["hello   ", "world"]


def test_read_lines_preserves_trailing_tabs(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("x\t\n", encoding="utf-8")
    assert read_lines(path) == ["x\t"]


def test_read_lines_empty_file(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("", encoding="utf-8")
    assert read_lines(path) == []


def test_read_lines_unicode(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("中文\nenglish\n", encoding="utf-8")
    assert read_lines(path) == ["中文", "english"]


def test_tail_last_two(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\nb\nc\nd\ne\n", encoding="utf-8")
    assert tail(path, 2) == ["d", "e"]


def test_tail_last_one(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\nb\nc\n", encoding="utf-8")
    assert tail(path, 1) == ["c"]


def test_tail_n_greater_than_file(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\nb\nc\n", encoding="utf-8")
    assert tail(path, 100) == ["a", "b", "c"]


def test_tail_full_file(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\nb\nc\n", encoding="utf-8")
    assert tail(path, 3) == ["a", "b", "c"]


def test_count_lines_basic(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\nb\nc\n", encoding="utf-8")
    assert count_lines(path) == 3


def test_count_lines_no_trailing_newline(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\nb\nc", encoding="utf-8")
    assert count_lines(path) == 3


def test_count_lines_empty_file(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("", encoding="utf-8")
    assert count_lines(path) == 0


def test_count_lines_single_line(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\n", encoding="utf-8")
    assert count_lines(path) == 1
