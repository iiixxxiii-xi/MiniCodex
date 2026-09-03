from datastore.jsonio import dump_json, load_json
from datastore.store import DocumentStore


def test_put_get():
    store = DocumentStore("unused.json")
    store.put("a", {"x": 1})
    assert store.get("a") == {"x": 1}


def test_get_missing_returns_none():
    store = DocumentStore("unused.json")
    assert store.get("missing") is None


def test_put_overwrites():
    store = DocumentStore("unused.json")
    store.put("a", {"x": 1})
    store.put("a", {"x": 2})
    assert store.get("a") == {"x": 2}


def test_delete_existing():
    store = DocumentStore("unused.json")
    store.put("a", {"x": 1})
    assert store.delete("a") is True
    assert store.get("a") is None


def test_delete_missing():
    store = DocumentStore("unused.json")
    assert store.delete("missing") is False


def test_contains():
    store = DocumentStore("unused.json")
    store.put("a", 1)
    assert "a" in store
    assert "b" not in store


def test_len_and_keys():
    store = DocumentStore("unused.json")
    store.put("a", 1)
    store.put("b", 2)
    assert len(store) == 2
    assert store.keys() == ["a", "b"]


def test_keys_insertion_order():
    store = DocumentStore("unused.json")
    store.put("z", 1)
    store.put("a", 2)
    store.put("m", 3)
    assert store.keys() == ["z", "a", "m"]


def test_empty_store():
    store = DocumentStore("unused.json")
    assert len(store) == 0
    assert store.keys() == []


def test_load_existing(tmp_path):
    path = tmp_path / "store.json"
    path.write_text('{"a": {"x": 1}}', encoding="utf-8")
    store = DocumentStore(str(path))
    assert store.get("a") == {"x": 1}


def test_flush_persists(tmp_path):
    path = str(tmp_path / "store.json")
    store = DocumentStore(path)
    store.put("a", {"x": 1})
    store.flush()
    reloaded = DocumentStore(path)
    assert reloaded.get("a") == {"x": 1}


def test_context_manager_flushes(tmp_path):
    path = str(tmp_path / "store.json")
    with DocumentStore(path) as store:
        store.put("a", {"x": 1})
    reloaded = DocumentStore(path)
    assert reloaded.get("a") == {"x": 1}


def test_flush_unicode(tmp_path):
    path = str(tmp_path / "store.json")
    store = DocumentStore(path)
    store.put("a", {"x": "中"})
    store.flush()
    raw = open(path, encoding="utf-8").read()
    assert "中" in raw


def test_close_marks_closed(tmp_path):
    path = str(tmp_path / "store.json")
    store = DocumentStore(path)
    store.put("a", {"x": 1})
    store.close()
    assert store.closed is True


def test_closed_before_close(tmp_path):
    path = str(tmp_path / "store.json")
    store = DocumentStore(path)
    assert store.closed is False


def test_dump_json_basic(tmp_path):
    path = str(tmp_path / "d.json")
    dump_json({"a": 1}, path)
    raw = open(path, encoding="utf-8").read()
    assert "a" in raw
    assert "1" in raw


def test_dump_json_unicode(tmp_path):
    path = str(tmp_path / "d.json")
    dump_json({"x": "中"}, path)
    raw = open(path, encoding="utf-8").read()
    assert "中" in raw


def test_load_json_basic(tmp_path):
    path = tmp_path / "d.json"
    path.write_text('{"a": 1}', encoding="utf-8")
    assert load_json(str(path)) == {"a": 1}


def test_load_json_roundtrip(tmp_path):
    path = str(tmp_path / "d.json")
    dump_json({"a": 1, "b": [1, 2]}, path)
    assert load_json(path) == {"a": 1, "b": [1, 2]}
