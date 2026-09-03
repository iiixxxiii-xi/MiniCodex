from fileops._open import open_text
from fileops.write import append_line, safe_write


def test_safe_write_basic(tmp_path):
    path = tmp_path / "out.txt"
    safe_write(path, "hello")
    assert path.read_text(encoding="utf-8") == "hello"


def test_safe_write_overwrites(tmp_path):
    path = tmp_path / "out.txt"
    safe_write(path, "first")
    safe_write(path, "second")
    assert path.read_text(encoding="utf-8") == "second"


def test_safe_write_truncates_existing(tmp_path):
    path = tmp_path / "out.txt"
    path.write_text("old content", encoding="utf-8")
    safe_write(path, "new")
    assert path.read_text(encoding="utf-8") == "new"


def test_safe_write_creates_parent_dirs(tmp_path):
    path = tmp_path / "a" / "b" / "out.txt"
    safe_write(path, "nested")
    assert path.read_text(encoding="utf-8") == "nested"


def test_append_line_adds_newline(tmp_path):
    path = tmp_path / "log.txt"
    append_line(path, "hello")
    assert path.read_text(encoding="utf-8") == "hello\n"


def test_append_line_multiple_lines(tmp_path):
    path = tmp_path / "log.txt"
    append_line(path, "first")
    append_line(path, "second")
    assert path.read_text(encoding="utf-8") == "first\nsecond\n"


def test_append_line_creates_file(tmp_path):
    path = tmp_path / "log.txt"
    append_line(path, "entry")
    assert path.exists()
    assert "entry" in path.read_text(encoding="utf-8")


def test_open_text_closes_handle(tmp_path):
    path = tmp_path / "data.txt"
    path.write_text("hello", encoding="utf-8")
    with open_text(path) as handle:
        assert handle.read() == "hello"
        assert handle.closed is False
    assert handle.closed is True


def test_open_text_closes_after_write(tmp_path):
    path = tmp_path / "out.txt"
    with open_text(path, "w") as handle:
        handle.write("hello")
    assert handle.closed is True
