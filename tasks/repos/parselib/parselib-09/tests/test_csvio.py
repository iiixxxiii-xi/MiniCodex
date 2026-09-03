from parselib.csvio import parse_csv


def test_csv_basic():
    assert parse_csv("a,b,c\n1,2,3\n") == [["a", "b", "c"], ["1", "2", "3"]]


def test_csv_quoted_comma():
    assert parse_csv('a,"b,c",d\n') == [["a", "b,c", "d"]]


def test_csv_quoted_newline():
    assert parse_csv('a,"line1\nline2",b\n') == [["a", "line1\nline2", "b"]]


def test_csv_quoted_quote():
    assert parse_csv('a,"say ""hi""",b\n') == [["a", 'say "hi"', "b"]]


def test_csv_empty_field():
    assert parse_csv("a,,c\n") == [["a", "", "c"]]


def test_csv_blank_lines_skipped():
    assert parse_csv("a,b\n\n\nc,d\n") == [["a", "b"], ["c", "d"]]


def test_csv_single_column():
    assert parse_csv("x\ny\nz\n") == [["x"], ["y"], ["z"]]
