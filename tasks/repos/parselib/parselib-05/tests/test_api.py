import parselib


def test_api_exports_parsers():
    for name in ["parse_ini", "parse_csv", "parse_kv", "load_json", "strip_comments", "split_words"]:
        assert hasattr(parselib, name), f"missing {name}"


def test_api_json_roundtrip():
    assert parselib.load_json('{"x": 1}') == {"x": 1}


def test_api_kv_roundtrip():
    assert parselib.parse_kv("a = b") == ("a", "b")


def test_api_csv_roundtrip():
    assert parselib.parse_csv("a,b\n") == [["a", "b"]]


def test_api_ini_roundtrip():
    assert parselib.parse_ini("[s]\na = 1\n") == {"s": {"a": "1"}}
