import fileops
from fileops.csvio import read_dicts, write_dicts
from fileops.scan import list_by_extension


def test_read_dicts_multiple_rows(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("name,age\nalice,30\nbob,25\ncarol,40\n", encoding="utf-8")
    assert read_dicts(path) == [
        {"name": "alice", "age": "30"},
        {"name": "bob", "age": "25"},
        {"name": "carol", "age": "40"},
    ]


def test_read_dicts_header_only(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("name,age\n", encoding="utf-8")
    assert read_dicts(path) == []


def test_read_dicts_unicode(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("name,城市\nalice,北京\n", encoding="utf-8")
    assert read_dicts(path) == [{"name": "alice", "城市": "北京"}]


def test_write_dicts_roundtrip(tmp_path):
    path = tmp_path / "data.csv"
    rows = [
        {"name": "alice", "age": "30"},
        {"name": "bob", "age": "25"},
    ]
    write_dicts(path, rows)
    assert read_dicts(path) == rows


def test_write_dicts_value_with_equals(tmp_path):
    path = tmp_path / "data.csv"
    write_dicts(path, [{"key": "a=b"}])
    assert read_dicts(path) == [{"key": "a=b"}]


def test_write_dicts_creates_file(tmp_path):
    path = tmp_path / "data.csv"
    write_dicts(path, [{"name": "alice"}])
    assert path.exists()
    assert "name" in path.read_text(encoding="utf-8")


def test_write_dicts_creates_parent_dirs(tmp_path):
    path = tmp_path / "x" / "y" / "data.csv"
    write_dicts(path, [{"name": "alice"}])
    assert read_dicts(path) == [{"name": "alice"}]


def test_list_by_extension_basic(tmp_path):
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "b.txt").write_text("2")
    (tmp_path / "c.csv").write_text("3")
    assert list_by_extension(tmp_path, "txt") == ["a.txt", "b.txt"]


def test_list_by_extension_case_insensitive(tmp_path):
    (tmp_path / "report.TXT").write_text("1")
    (tmp_path / "note.txt").write_text("2")
    assert list_by_extension(tmp_path, "txt") == ["note.txt", "report.TXT"]


def test_list_by_extension_leading_dot(tmp_path):
    (tmp_path / "a.txt").write_text("1")
    assert list_by_extension(tmp_path, ".txt") == ["a.txt"]


def test_list_by_extension_skips_directories(tmp_path):
    (tmp_path / "notes.txt").mkdir()
    (tmp_path / "a.txt").write_text("1")
    assert list_by_extension(tmp_path, "txt") == ["a.txt"]


def test_list_by_extension_sorted(tmp_path):
    (tmp_path / "c.txt").write_text("1")
    (tmp_path / "a.txt").write_text("2")
    (tmp_path / "b.txt").write_text("3")
    assert list_by_extension(tmp_path, "txt") == ["a.txt", "b.txt", "c.txt"]


def test_api_all_public_names_present():
    for name in [
        "read_lines",
        "tail",
        "count_lines",
        "safe_write",
        "append_line",
        "read_dicts",
        "write_dicts",
        "list_by_extension",
    ]:
        assert hasattr(fileops, name), f"missing {name}"


def test_api_tail():
    assert callable(fileops.tail)


def test_api_read_lines():
    assert callable(fileops.read_lines)


def test_api_safe_write(tmp_path):
    path = tmp_path / "out.txt"
    fileops.safe_write(path, "hello")
    assert path.read_text(encoding="utf-8") == "hello"


def test_api_list_by_extension(tmp_path):
    (tmp_path / "a.txt").write_text("1")
    assert fileops.list_by_extension(tmp_path, "txt") == ["a.txt"]
