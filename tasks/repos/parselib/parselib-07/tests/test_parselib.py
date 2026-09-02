import parselib


def test_parse_json_blank():
    assert parselib.parse_json("   ") == {}


def test_parse_json_empty():
    assert parselib.parse_json("") == {}


def test_parse_json_object():
    assert parselib.parse_json('{"a": 1}') == {"a": 1}


def test_strip_comments_basic():
    assert parselib.strip_comments("a = 1  # inline\nb = 2\n") == "a = 1\nb = 2"


def test_strip_comments_full_line():
    assert parselib.strip_comments("# full comment\ncode\n") == "\ncode"


def test_strip_comments_no_comment():
    assert parselib.strip_comments("plain\ntext\n") == "plain\ntext"


def test_parse_csv_quoted_field():
    assert parselib.parse_csv('a,"b,c",d\n') == [["a", "b,c", "d"]]


def test_parse_csv_quoted_two():
    assert parselib.parse_csv('"x,y","z,w"\n') == [["x,y", "z,w"]]


def test_parse_csv_basic():
    assert parselib.parse_csv("x,y\n1,2\n") == [["x", "y"], ["1", "2"]]


def test_parse_kv_value_with_equals():
    assert parselib.parse_kv("url=https://a.com?x=1\n") == {"url": "https://a.com?x=1"}


def test_parse_kv_multiple_equals():
    assert parselib.parse_kv("a=b=c\n") == {"a": "b=c"}


def test_parse_kv_basic():
    assert parselib.parse_kv("name=alice\nage=30\n") == {"name": "alice", "age": "30"}


def test_parse_ini_top_level():
    text = "title=My App\n[server]\nhost=localhost\n"
    assert parselib.parse_ini(text)["title"] == "My App"


def test_parse_ini_top_level_only():
    assert parselib.parse_ini("title=My App\n") == {"title": "My App"}


def test_parse_ini_sections():
    text = "[server]\nhost=localhost\n[db]\nport=5432\n"
    assert parselib.parse_ini(text) == {"server": {"host": "localhost"}, "db": {"port": "5432"}}


def test_sum_column_floats():
    assert parselib.sum_column([["1.5"], ["2.5"]], 0) == 4.0


def test_sum_column_mixed():
    assert parselib.sum_column([["1"], ["2.5"]], 0) == 3.5


def test_sum_column_basic():
    assert parselib.sum_column([["1", "2"], ["3", "4"]], 0) == 4.0


def test_get_field_missing():
    assert parselib.get_field({}, "x") is None


def test_get_field_missing_default():
    assert parselib.get_field({"a": 1}, "b", default=0) == 0


def test_get_field_present():
    assert parselib.get_field({"a": 1}, "a") == 1


def test_split_words_multiple_spaces():
    assert parselib.split_words("a  b\tc") == ["a", "b", "c"]


def test_split_words_leading():
    assert parselib.split_words("  a  b  ") == ["a", "b"]


def test_split_words_basic():
    assert parselib.split_words("hello world") == ["hello", "world"]
