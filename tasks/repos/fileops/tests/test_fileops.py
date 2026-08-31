import fileops


def test_read_lines(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("hello world\nfoo bar\n")
    assert fileops.read_lines(str(p)) == ["hello world", "foo bar"]


def test_count_lines(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a\nb\nc\n")
    assert fileops.count_lines(str(p)) == 3


def test_tail(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a\nb\nc\nd\n")
    assert fileops.tail(str(p), 2) == ["c", "d"]
    assert fileops.tail(str(p), 0) == []


def test_parse_kv(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("name=alice\nurl=https://a.com?x=1\n")
    assert fileops.parse_kv(str(p)) == {"name": "alice", "url": "https://a.com?x=1"}


def test_list_by_extension(tmp_path):
    (tmp_path / "a.txt").write_text("")
    (tmp_path / "b.TXT").write_text("")
    (tmp_path / "c.csv").write_text("")
    assert fileops.list_by_extension(str(tmp_path), ".txt") == ["a.txt", "b.TXT"]


def test_safe_write(tmp_path):
    target = tmp_path / "sub" / "f.txt"
    fileops.safe_write(str(target), "hello")
    assert target.read_text() == "hello"


def test_read_csv_as_dicts(tmp_path):
    p = tmp_path / "f.csv"
    p.write_text("name,age\nAlice,30\n")
    assert fileops.read_csv_as_dicts(str(p)) == [{"name": "Alice", "age": "30"}]


def test_append_line(tmp_path):
    p = tmp_path / "f.txt"
    fileops.append_line(str(p), "a")
    fileops.append_line(str(p), "b")
    assert p.read_text() == "a\nb\n"
