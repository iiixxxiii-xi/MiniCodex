from datastore.query import aggregate, dedupe, filter_records, group_by, group_csv, select_fields


def test_filter_records_basic():
    assert filter_records([1, 2, 3, 4], lambda x: x > 2) == [3, 4]


def test_filter_records_empty():
    assert filter_records([], lambda x: True) == []


def test_group_by_basic():
    records = [{"g": "a", "v": 1}, {"g": "b", "v": 2}]
    assert group_by(records, lambda r: r["g"]) == {
        "a": [{"g": "a", "v": 1}],
        "b": [{"g": "b", "v": 2}],
    }


def test_group_by_multiple_per_group():
    records = [{"g": "a", "v": 1}, {"g": "a", "v": 2}, {"g": "b", "v": 3}]
    assert group_by(records, lambda r: r["g"]) == {
        "a": [{"g": "a", "v": 1}, {"g": "a", "v": 2}],
        "b": [{"g": "b", "v": 3}],
    }


def test_group_by_empty():
    assert group_by([], lambda r: r) == {}


def test_dedupe_whole_record():
    assert dedupe([1, 2, 2, 3, 1]) == [1, 2, 3]


def test_dedupe_by_field():
    records = [{"id": 1, "n": "a"}, {"id": 1, "n": "b"}, {"id": 2, "n": "c"}]
    assert dedupe(records, "id") == [{"id": 1, "n": "a"}, {"id": 2, "n": "c"}]


def test_dedupe_empty():
    assert dedupe([]) == []


def test_aggregate_sum():
    assert aggregate([{"v": 1}, {"v": 2}, {"v": 3}], "v", sum) == 6


def test_aggregate_empty():
    assert aggregate([], "v", min, default=0) == 0


def test_select_fields_basic():
    records = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    assert select_fields(records, "a") == [{"a": 1}, {"a": 3}]


def test_group_csv_basic():
    text = "category,value\na,1\na,2\nb,3"
    assert group_csv(text, "category") == {
        "a": [{"category": "a", "value": "1"}, {"category": "a", "value": "2"}],
        "b": [{"category": "b", "value": "3"}],
    }
