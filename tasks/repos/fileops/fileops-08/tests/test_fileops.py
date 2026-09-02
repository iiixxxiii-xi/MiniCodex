import fileops


def test_read_lines_basic(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("hello world\nfoo bar\n", encoding="utf-8")
    assert fileops.read_lines(str(p)) == ["hello world", "foo bar"]


def test_read_lines_words(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("one two\nthree\n", encoding="utf-8")
    assert fileops.read_lines(str(p)) == ["one two", "three"]


def test_read_lines_no_trailing_newline(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("hello\nworld", encoding="utf-8")
    assert fileops.read_lines(str(p)) == ["hello", "world"]


def test_count_lines_basic(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a\nb\nc\n", encoding="utf-8")
    assert fileops.count_lines(str(p)) == 3


def test_count_lines_empty(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("", encoding="utf-8")
    assert fileops.count_lines(str(p)) == 0


def test_tail_zero(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a\nb\n", encoding="utf-8")
    assert fileops.tail(str(p), 0) == []


def test_tail_negative(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a\nb\n", encoding="utf-8")
    assert fileops.tail(str(p), -1) == []


def test_tail_basic(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a\nb\nc\nd\n", encoding="utf-8")
    assert fileops.tail(str(p), 2) == ["c", "d"]


def test_parse_kv_value_with_equals(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("url=https://a.com?x=1\n", encoding="utf-8")
    assert fileops.parse_kv(str(p)) == {"url": "https://a.com?x=1"}


def test_parse_kv_multiple_equals(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a=b=c\n", encoding="utf-8")
    assert fileops.parse_kv(str(p)) == {"a": "b=c"}


def test_parse_kv_basic(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a=1\nb=2\n", encoding="utf-8")
    assert fileops.parse_kv(str(p)) == {"a": "1", "b": "2"}


def test_list_by_extension_case(tmp_path):
    (tmp_path / "a.txt").write_text("")
    (tmp_path / "b.TXT").write_text("")
    (tmp_path / "c.csv").write_text("")
    assert fileops.list_by_extension(str(tmp_path), ".txt") == ["a.txt", "b.TXT"]


def test_list_by_extension_upper_only(tmp_path):
    (tmp_path / "DATA.TXT").write_text("")
    assert fileops.list_by_extension(str(tmp_path), ".txt") == ["DATA.TXT"]


def test_list_by_extension_empty(tmp_path):
    (tmp_path / "a.txt").write_text("")
    assert fileops.list_by_extension(str(tmp_path), ".csv") == []


def test_safe_write_creates_parent(tmp_path):
    target = tmp_path / "sub" / "f.txt"
    fileops.safe_write(str(target), "hello")
    assert target.read_text(encoding="utf-8") == "hello"


def test_safe_write_deep_parent(tmp_path):
    target = tmp_path / "a" / "b" / "c" / "f.txt"
    fileops.safe_write(str(target), "deep")
    assert target.read_text(encoding="utf-8") == "deep"


def test_safe_write_overwrites(tmp_path):
    target = tmp_path / "f.txt"
    fileops.safe_write(str(target), "one")
    fileops.safe_write(str(target), "two")
    assert target.read_text(encoding="utf-8") == "two"


def test_read_csv_as_dicts_skips_header(tmp_path):
    p = tmp_path / "f.csv"
    p.write_text("name,age\nAlice,30\nBob,40\n", encoding="utf-8")
    rows = fileops.read_csv_as_dicts(str(p))
    assert rows == [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "40"}]


def test_read_csv_as_dicts_basic(tmp_path):
    p = tmp_path / "f.csv"
    p.write_text("name,age\nAlice,30\n", encoding="utf-8")
    assert fileops.read_csv_as_dicts(str(p)) == [{"name": "Alice", "age": "30"}]


def test_append_line_basic(tmp_path):
    p = tmp_path / "f.txt"
    fileops.append_line(str(p), "a")
    fileops.append_line(str(p), "b")
    assert p.read_text(encoding="utf-8") == "a\nb\n"


def test_append_line_creates_file(tmp_path):
    p = tmp_path / "f.txt"
    fileops.append_line(str(p), "hello")
    assert p.read_text(encoding="utf-8") == "hello\n"
