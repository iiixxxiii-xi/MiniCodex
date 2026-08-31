import datastore


def test_parse_json():
    assert datastore.parse_json('{"a": 1}') == {"a": 1}
    assert datastore.parse_json("") == {}


def test_parse_csv():
    assert datastore.parse_csv("a, b\n1, 2") == [["a", "b"], ["1", "2"]]


def test_filter_records():
    records = [{"k": 1}, {"k": 2}, {"k": 1}]
    assert datastore.filter_records(records, "k", 1) == [{"k": 1}, {"k": 1}]


def test_group_by():
    records = [{"k": "a", "v": 1}, {"v": 2}, {"k": "a", "v": 3}]
    assert datastore.group_by(records, "k") == {
        "a": [{"k": "a", "v": 1}, {"k": "a", "v": 3}],
        "unknown": [{"v": 2}],
    }


def test_to_csv():
    assert datastore.to_csv([["a", "b"], ["c", "d"]]) == "a,b\nc,d"
    assert datastore.to_csv([["a", "b"]], delimiter=";") == "a;b"


def test_summarize():
    assert datastore.summarize(["1.5", "2.5"]) == 4.0


def test_nested_get():
    assert datastore.nested_get({"a": {"b": 1}}, "a.b") == 1
    assert datastore.nested_get({"a": {}}, "a.b.c") is None


def test_dedupe():
    records = [{"id": 1, "v": "a"}, {"id": 1, "v": "b"}, {"id": 2, "v": "c"}]
    assert datastore.dedupe(records, "id") == [{"id": 1, "v": "a"}, {"id": 2, "v": "c"}]
