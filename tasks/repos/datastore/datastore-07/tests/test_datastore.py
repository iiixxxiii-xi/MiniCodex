import datastore


def test_parse_json_empty():
    assert datastore.parse_json("") == {}


def test_parse_json_whitespace():
    assert datastore.parse_json("   ") == {}


def test_parse_json_object():
    assert datastore.parse_json('{"a": 1}') == {"a": 1}


def test_parse_csv_strips():
    assert datastore.parse_csv("a, b\n1, 2") == [["a", "b"], ["1", "2"]]


def test_parse_csv_extra_spaces():
    assert datastore.parse_csv(" x , y ") == [["x", "y"]]


def test_filter_records_match():
    records = [{"k": 1}, {"k": 2}, {"k": 1}]
    assert datastore.filter_records(records, "k", 1) == [{"k": 1}, {"k": 1}]


def test_filter_records_no_match():
    records = [{"k": 1}, {"k": 2}]
    assert datastore.filter_records(records, "k", 9) == []


def test_group_by_missing_key():
    records = [{"v": 2}]
    assert datastore.group_by(records, "k") == {"unknown": [{"v": 2}]}


def test_group_by_present():
    records = [{"k": "a", "v": 1}, {"v": 2}, {"k": "a", "v": 3}]
    assert datastore.group_by(records, "k")["a"] == [{"k": "a", "v": 1}, {"k": "a", "v": 3}]


def test_to_csv_custom_delimiter():
    assert datastore.to_csv([["a", "b"]], delimiter=";") == "a;b"


def test_to_csv_custom_pipe():
    assert datastore.to_csv([["a", "b"]], delimiter="|") == "a|b"


def test_to_csv_default():
    assert datastore.to_csv([["a", "b"], ["c", "d"]]) == "a,b\nc,d"


def test_summarize_floats():
    assert datastore.summarize(["1.5", "2.5"]) == 4.0


def test_summarize_mixed():
    assert datastore.summarize(["1", "2.5"]) == 3.5


def test_summarize_ints():
    assert datastore.summarize([1, 2, 3]) == 6.0


def test_nested_get_missing():
    assert datastore.nested_get({"a": {}}, "a.b.c") is None


def test_nested_get_deep_missing():
    assert datastore.nested_get({"a": {"b": 1}}, "a.x.y") is None


def test_nested_get_present():
    assert datastore.nested_get({"a": {"b": 1}}, "a.b") == 1


def test_dedupe_keeps_first():
    records = [{"id": 1, "v": "a"}, {"id": 1, "v": "b"}, {"id": 2, "v": "c"}]
    assert datastore.dedupe(records, "id") == [{"id": 1, "v": "a"}, {"id": 2, "v": "c"}]


def test_dedupe_all_unique():
    records = [{"id": 1}, {"id": 2}]
    assert datastore.dedupe(records, "id") == [{"id": 1}, {"id": 2}]
