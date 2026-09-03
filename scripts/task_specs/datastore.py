"""Repo spec: ``datastore`` — a small JSON-backed storage engine.

A realistic multi-module package: a ``jsonio`` serialization helper, a
``store`` document store with explicit resource management (flush/close), a
``csvio`` import/export layer that honours quoted fields, and a ``query``
filter/group/dedupe/aggregate layer. Modules import each other
(``store`` -> ``jsonio``, ``query`` -> ``csvio``), so bugs in a shared helper
surface through the modules that consume it, in addition to a multi-file
``ensure_ascii`` serialization bug and a resource-management bug
(flush-on-close missing).
"""

REPO = "datastore"

FILES = {
    "datastore/__init__.py": '''"""A small JSON-backed document store with CSV I/O and a query layer.

Public API:
- ``DocumentStore`` — key -> document persistence with explicit close.
- ``parse_csv`` / ``parse_csv_dicts`` / ``to_csv`` — CSV import/export.
- ``filter_records`` / ``group_by`` / ``dedupe`` / ``aggregate`` — query helpers.
- ``dump_json`` / ``load_json`` — JSON serialization helpers.
"""

from datastore.csvio import parse_csv, parse_csv_dicts, to_csv
from datastore.jsonio import dump_json, load_json
from datastore.query import aggregate, dedupe, filter_records, group_by
from datastore.store import DocumentStore

__all__ = [
    "DocumentStore",
    "parse_csv",
    "parse_csv_dicts",
    "to_csv",
    "filter_records",
    "group_by",
    "dedupe",
    "aggregate",
    "dump_json",
    "load_json",
]
''',
    "datastore/jsonio.py": '''"""JSON serialization helpers used across the datastore package."""

import json


def dump_json(obj, path: str) -> None:
    """Serialize ``obj`` to ``path`` as indented JSON (UTF-8, non-ASCII kept)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_json(path: str):
    """Deserialize the JSON document stored at ``path``."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
''',
    "datastore/store.py": '''"""A JSON-backed document store with explicit resource management."""

import json
import os

from datastore.jsonio import load_json


class DocumentStore:
    """A small key -> document store persisted to a JSON file.

    Documents live in memory and are persisted by ``flush`` or ``close``. The
    store supports the context-manager protocol so ``with DocumentStore(...) as
    store:`` flushes and closes cleanly.
    """

    def __init__(self, path: str):
        self.path = path
        self._docs = {}
        self._closed = False
        if os.path.exists(path):
            self._docs = load_json(path)

    def put(self, key, document) -> None:
        """Store ``document`` under ``key``."""
        self._docs[key] = document

    def get(self, key):
        """Return the document stored under ``key``, or ``None`` if absent."""
        return self._docs.get(key)

    def delete(self, key) -> bool:
        """Remove ``key``; return ``True`` if it was present, else ``False``."""
        if key in self._docs:
            del self._docs[key]
            return True
        return False

    def __contains__(self, key) -> bool:
        return key in self._docs

    def keys(self) -> list:
        """Return the store's keys in insertion order."""
        return list(self._docs.keys())

    def __len__(self) -> int:
        return len(self._docs)

    def flush(self) -> None:
        """Persist the in-memory documents to disk."""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._docs, f, ensure_ascii=False, indent=2)

    def close(self) -> None:
        """Persist any pending changes and mark the store closed."""
        self.flush()
        self._closed = True

    @property
    def closed(self) -> bool:
        """True once ``close`` has been called."""
        return self._closed

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
''',
    "datastore/csvio.py": '''"""CSV import/export honouring quoted fields."""

import csv
import io


def parse_csv(text: str, has_header: bool = True):
    """Parse CSV ``text`` into ``(header, rows)``.

    Quoted fields (containing commas, quotes, or newlines) are handled per the
    standard CSV dialect. When ``has_header`` is true the first record is the
    header; otherwise ``header`` is ``None``.
    """
    reader = csv.reader(io.StringIO(text))
    rows = [row for row in reader]
    if has_header and rows:
        return rows[0], rows[1:]
    return None, rows


def parse_csv_dicts(text: str) -> list:
    """Parse CSV ``text`` into a list of dicts keyed by the header row."""
    header, rows = parse_csv(text, has_header=True)
    if header is None:
        return []
    return [dict(zip(header, row)) for row in rows]


def to_csv(rows, header=None) -> str:
    """Serialize ``rows`` (each an iterable of fields) to a CSV string.

    Fields that need it are quoted on output. When ``header`` is given it is
    written as the first row.
    """
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\\n")
    if header is not None:
        writer.writerow(header)
    writer.writerows(rows)
    return buf.getvalue()
''',
    "datastore/query.py": '''"""Filter, group-by, dedupe, and aggregation helpers over record lists."""

from datastore.csvio import parse_csv_dicts


def filter_records(records, predicate):
    """Return the records for which ``predicate(record)`` is truthy."""
    return [record for record in records if predicate(record)]


def group_by(records, key):
    """Group ``records`` into a dict mapping ``key(record)`` -> list of records."""
    groups = {}
    for record in records:
        k = key(record)
        groups.setdefault(k, []).append(record)
    return groups


def dedupe(records, key=None):
    """Return ``records`` with duplicates removed, keeping first occurrence.

    ``key`` may be a callable or a string field name; by default the whole
    record is compared.
    """
    seen = set()
    out = []
    for record in records:
        if key is None:
            k = record
        elif callable(key):
            k = key(record)
        else:
            k = record[key]
        if k in seen:
            continue
        seen.add(k)
        out.append(record)
    return out


def aggregate(records, key, func, default=None):
    """Apply ``func`` to the list of values at ``key`` across ``records``.

    Returns ``default`` when there are no records.
    """
    values = [record[key] for record in records]
    if not values:
        return default
    return func(values)


def select_fields(records, *fields):
    """Project each record down to just the given ``fields``."""
    return [{field: record[field] for field in fields} for record in records]


def group_csv(text, key):
    """Parse CSV ``text`` into record dicts and group them by ``key``."""
    records = parse_csv_dicts(text)
    return group_by(records, lambda record: record[key])
''',
}

TESTS = {
    "tests/test_store.py": '''from datastore.jsonio import dump_json, load_json
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
''',
    "tests/test_csv.py": '''from datastore.csvio import parse_csv, parse_csv_dicts, to_csv


def test_parse_csv_basic():
    header, rows = parse_csv("name,age\\nAlice,30\\nBob,25")
    assert header == ["name", "age"]
    assert rows == [["Alice", "30"], ["Bob", "25"]]


def test_parse_csv_quoted_comma():
    header, rows = parse_csv("name,note\\nAlice,\\"hello, world\\"")
    assert rows == [["Alice", "hello, world"]]


def test_parse_csv_no_header():
    header, rows = parse_csv("a,b\\n1,2", has_header=False)
    assert header is None
    assert rows == [["a", "b"], ["1", "2"]]


def test_parse_csv_empty():
    header, rows = parse_csv("")
    assert header is None
    assert rows == []


def test_parse_csv_dicts_basic():
    records = parse_csv_dicts("name,age\\nAlice,30\\nBob,25")
    assert records == [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}]


def test_parse_csv_dicts_empty():
    assert parse_csv_dicts("") == []


def test_to_csv_basic():
    assert to_csv([["a", "b"], ["1", "2"]]) == "a,b\\n1,2\\n"


def test_to_csv_with_header():
    assert to_csv([["1", "2"]], header=["a", "b"]) == "a,b\\n1,2\\n"


def test_to_csv_quotes_comma():
    assert to_csv([["a", "b,c"]]) == "a,\\"b,c\\"\\n"


def test_to_csv_no_header():
    assert to_csv([["x"]]) == "x\\n"
''',
    "tests/test_query.py": '''from datastore.query import aggregate, dedupe, filter_records, group_by, group_csv, select_fields


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
    text = "category,value\\na,1\\na,2\\nb,3"
    assert group_csv(text, "category") == {
        "a": [{"category": "a", "value": "1"}, {"category": "a", "value": "2"}],
        "b": [{"category": "b", "value": "3"}],
    }
''',
}

TASKS = [
    {
        "id": "datastore-01",
        "instruction": (
            "Fix `DocumentStore.get` in `datastore/store.py` so it returns `None` for a missing "
            "key instead of raising `KeyError`. It currently indexes `self._docs[key]` directly, "
            "which crashes callers that look up an absent key."
        ),
        "difficulty": "easy",
        "category": "store",
        "lines": 1,
        "bug": [
            (
                "datastore/store.py",
                "        return self._docs.get(key)",
                "        return self._docs[key]",
            )
        ],
        "fail_to_pass": ["tests/test_store.py::test_get_missing_returns_none"],
        "pass_to_pass": [
            "tests/test_store.py::test_put_get",
            "tests/test_store.py::test_put_overwrites",
            "tests/test_store.py::test_contains",
        ],
    },
    {
        "id": "datastore-02",
        "instruction": (
            "Fix `DocumentStore.delete` in `datastore/store.py` so it returns `False` when the key "
            "was not present. It currently reports `True` even when nothing was removed, so callers "
            "cannot tell whether a delete actually happened."
        ),
        "difficulty": "easy",
        "category": "store",
        "lines": 3,
        "bug": [
            (
                "datastore/store.py",
                (
                    "        if key in self._docs:\n"
                    "            del self._docs[key]\n"
                    "            return True\n"
                    "        return False"
                ),
                (
                    "        if key in self._docs:\n"
                    "            del self._docs[key]\n"
                    "        return True"
                ),
            )
        ],
        "fail_to_pass": ["tests/test_store.py::test_delete_missing"],
        "pass_to_pass": [
            "tests/test_store.py::test_delete_existing",
            "tests/test_store.py::test_contains",
            "tests/test_store.py::test_put_get",
        ],
    },
    {
        "id": "datastore-03",
        "instruction": (
            "Fix `to_csv` in `datastore/csvio.py` so it emits the header row. It currently ignores "
            "the `header` argument entirely, so callers that pass a header get data-only output."
        ),
        "difficulty": "easy",
        "category": "csv",
        "lines": 2,
        "bug": [
            (
                "datastore/csvio.py",
                (
                    "    if header is not None:\n"
                    "        writer.writerow(header)\n"
                    "    writer.writerows(rows)"
                ),
                "    writer.writerows(rows)",
            )
        ],
        "fail_to_pass": ["tests/test_csv.py::test_to_csv_with_header"],
        "pass_to_pass": [
            "tests/test_csv.py::test_to_csv_basic",
            "tests/test_csv.py::test_to_csv_quotes_comma",
            "tests/test_csv.py::test_to_csv_no_header",
        ],
    },
    {
        "id": "datastore-04",
        "instruction": (
            "Fix `filter_records` in `datastore/query.py` so it keeps the records that MATCH the "
            "predicate. It currently keeps the records for which the predicate is false, returning "
            "the inverse of the expected result."
        ),
        "difficulty": "easy",
        "category": "query",
        "lines": 1,
        "bug": [
            (
                "datastore/query.py",
                "    return [record for record in records if predicate(record)]",
                "    return [record for record in records if not predicate(record)]",
            )
        ],
        "fail_to_pass": ["tests/test_query.py::test_filter_records_basic"],
        "pass_to_pass": [
            "tests/test_query.py::test_filter_records_empty",
            "tests/test_query.py::test_group_by_basic",
        ],
    },
    {
        "id": "datastore-05",
        "instruction": (
            "Fix `parse_csv_dicts` in `datastore/csvio.py` so each row's fields map to the correct "
            "column header. The zip is in the wrong order, so keys and values are swapped, and "
            "`group_csv` in `datastore/query.py` (which relies on these dicts) raises `KeyError`."
        ),
        "difficulty": "medium",
        "category": "csv",
        "lines": 1,
        "bug": [
            (
                "datastore/csvio.py",
                "    return [dict(zip(header, row)) for row in rows]",
                "    return [dict(zip(row, header)) for row in rows]",
            )
        ],
        "fail_to_pass": [
            "tests/test_csv.py::test_parse_csv_dicts_basic",
            "tests/test_query.py::test_group_csv_basic",
        ],
        "pass_to_pass": [
            "tests/test_csv.py::test_parse_csv_basic",
            "tests/test_csv.py::test_parse_csv_no_header",
            "tests/test_csv.py::test_parse_csv_dicts_empty",
        ],
    },
    {
        "id": "datastore-06",
        "instruction": (
            "Fix `parse_csv` in `datastore/csvio.py` so it returns `(None, [])` for empty input "
            "instead of crashing. It currently tries to read `rows[0]` even when there are no rows, "
            "raising `IndexError`."
        ),
        "difficulty": "medium",
        "category": "csv",
        "lines": 1,
        "bug": [
            (
                "datastore/csvio.py",
                "    if has_header and rows:",
                "    if has_header:",
            )
        ],
        "fail_to_pass": ["tests/test_csv.py::test_parse_csv_empty"],
        "pass_to_pass": [
            "tests/test_csv.py::test_parse_csv_basic",
            "tests/test_csv.py::test_parse_csv_no_header",
            "tests/test_csv.py::test_parse_csv_quoted_comma",
        ],
    },
    {
        "id": "datastore-07",
        "instruction": (
            "Fix `aggregate` in `datastore/query.py` so it returns the `default` value when the "
            "input is empty. It currently calls `func` on an empty list, which raises for `min`/"
            "`max` instead of falling back to `default`."
        ),
        "difficulty": "medium",
        "category": "query",
        "lines": 2,
        "bug": [
            (
                "datastore/query.py",
                (
                    "    values = [record[key] for record in records]\n"
                    "    if not values:\n"
                    "        return default\n"
                    "    return func(values)"
                ),
                (
                    "    values = [record[key] for record in records]\n"
                    "    return func(values)"
                ),
            )
        ],
        "fail_to_pass": ["tests/test_query.py::test_aggregate_empty"],
        "pass_to_pass": [
            "tests/test_query.py::test_aggregate_sum",
            "tests/test_query.py::test_filter_records_basic",
        ],
    },
    {
        "id": "datastore-08",
        "instruction": (
            "Fix `dedupe` in `datastore/query.py` so that when `key` is a string it dedupes by that "
            "FIELD, not by the string itself. It currently compares the literal key string for every "
            "record, collapsing the whole list down to a single record."
        ),
        "difficulty": "medium",
        "category": "query",
        "lines": 1,
        "bug": [
            (
                "datastore/query.py",
                "            k = record[key]",
                "            k = key",
            )
        ],
        "fail_to_pass": ["tests/test_query.py::test_dedupe_by_field"],
        "pass_to_pass": [
            "tests/test_query.py::test_dedupe_whole_record",
            "tests/test_query.py::test_dedupe_empty",
            "tests/test_query.py::test_select_fields_basic",
        ],
    },
    {
        "id": "datastore-09",
        "instruction": (
            "Fix `group_by` in `datastore/query.py` so records that share a key are accumulated into "
            "a list. It currently overwrites the group each time, keeping only the last record per "
            "key."
        ),
        "difficulty": "medium",
        "category": "query",
        "lines": 1,
        "bug": [
            (
                "datastore/query.py",
                "        groups.setdefault(k, []).append(record)",
                "        groups[k] = [record]",
            )
        ],
        "fail_to_pass": ["tests/test_query.py::test_group_by_multiple_per_group"],
        "pass_to_pass": [
            "tests/test_query.py::test_group_by_basic",
            "tests/test_query.py::test_group_by_empty",
        ],
    },
    {
        "id": "datastore-10",
        "instruction": (
            "Fix `load_json` in `datastore/jsonio.py` so it returns the parsed document as-is. It "
            "currently unwraps a non-existent `documents` key, so `DocumentStore` (which loads its "
            "state through this helper) opens existing files as empty."
        ),
        "difficulty": "hard",
        "category": "serialization",
        "lines": 1,
        "bug": [
            (
                "datastore/jsonio.py",
                "        return json.load(f)",
                '        return json.load(f).get("documents", {})',
            )
        ],
        "fail_to_pass": [
            "tests/test_store.py::test_load_existing",
            "tests/test_store.py::test_flush_persists",
            "tests/test_store.py::test_load_json_basic",
        ],
        "pass_to_pass": [
            "tests/test_store.py::test_put_get",
            "tests/test_store.py::test_flush_unicode",
            "tests/test_store.py::test_close_marks_closed",
            "tests/test_store.py::test_dump_json_basic",
        ],
    },
    {
        "id": "datastore-11",
        "instruction": (
            "Fix `DocumentStore.close` in `datastore/store.py` so it flushes pending changes before "
            "marking the store closed. Closing through the context manager currently drops unflushed "
            "writes, so data written inside a `with` block is lost."
        ),
        "difficulty": "hard",
        "category": "resource",
        "lines": 1,
        "bug": [
            (
                "datastore/store.py",
                "        self.flush()\n        self._closed = True",
                "        self._closed = True",
            )
        ],
        "fail_to_pass": ["tests/test_store.py::test_context_manager_flushes"],
        "pass_to_pass": [
            "tests/test_store.py::test_close_marks_closed",
            "tests/test_store.py::test_flush_persists",
            "tests/test_store.py::test_closed_before_close",
        ],
    },
    {
        "id": "datastore-12",
        "instruction": (
            "Fix `parse_csv` in `datastore/csvio.py` so it honours quoted fields. It currently "
            "disables quoting, so a field like `\"hello, world\"` is split at its comma into two "
            "fields instead of staying intact."
        ),
        "difficulty": "hard",
        "category": "csv",
        "lines": 1,
        "bug": [
            (
                "datastore/csvio.py",
                "    reader = csv.reader(io.StringIO(text))",
                "    reader = csv.reader(io.StringIO(text), quoting=csv.QUOTE_NONE)",
            )
        ],
        "fail_to_pass": ["tests/test_csv.py::test_parse_csv_quoted_comma"],
        "pass_to_pass": [
            "tests/test_csv.py::test_parse_csv_basic",
            "tests/test_csv.py::test_parse_csv_no_header",
        ],
    },
    {
        "id": "datastore-13",
        "instruction": (
            "Fix unicode serialization in `datastore/jsonio.py` and `datastore/store.py` so non-"
            "ASCII characters are written literally instead of escaped. Both `dump_json` and "
            "`DocumentStore.flush` currently set `ensure_ascii=True`, escaping non-ASCII output."
        ),
        "difficulty": "hard",
        "category": "serialization",
        "lines": 2,
        "bug": [
            (
                "datastore/jsonio.py",
                "        json.dump(obj, f, ensure_ascii=False, indent=2)",
                "        json.dump(obj, f, ensure_ascii=True, indent=2)",
            ),
            (
                "datastore/store.py",
                "            json.dump(self._docs, f, ensure_ascii=False, indent=2)",
                "            json.dump(self._docs, f, ensure_ascii=True, indent=2)",
            ),
        ],
        "fail_to_pass": [
            "tests/test_store.py::test_dump_json_unicode",
            "tests/test_store.py::test_flush_unicode",
        ],
        "pass_to_pass": [
            "tests/test_store.py::test_dump_json_basic",
            "tests/test_store.py::test_flush_persists",
            "tests/test_store.py::test_load_json_roundtrip",
        ],
    },
]
