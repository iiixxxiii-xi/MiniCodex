from datastore.csvio import parse_csv, parse_csv_dicts, to_csv


def test_parse_csv_basic():
    header, rows = parse_csv("name,age\nAlice,30\nBob,25")
    assert header == ["name", "age"]
    assert rows == [["Alice", "30"], ["Bob", "25"]]


def test_parse_csv_quoted_comma():
    header, rows = parse_csv("name,note\nAlice,\"hello, world\"")
    assert rows == [["Alice", "hello, world"]]


def test_parse_csv_no_header():
    header, rows = parse_csv("a,b\n1,2", has_header=False)
    assert header is None
    assert rows == [["a", "b"], ["1", "2"]]


def test_parse_csv_empty():
    header, rows = parse_csv("")
    assert header is None
    assert rows == []


def test_parse_csv_dicts_basic():
    records = parse_csv_dicts("name,age\nAlice,30\nBob,25")
    assert records == [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}]


def test_parse_csv_dicts_empty():
    assert parse_csv_dicts("") == []


def test_to_csv_basic():
    assert to_csv([["a", "b"], ["1", "2"]]) == "a,b\n1,2\n"


def test_to_csv_with_header():
    assert to_csv([["1", "2"]], header=["a", "b"]) == "a,b\n1,2\n"


def test_to_csv_quotes_comma():
    assert to_csv([["a", "b,c"]]) == "a,\"b,c\"\n"


def test_to_csv_no_header():
    assert to_csv([["x"]]) == "x\n"
