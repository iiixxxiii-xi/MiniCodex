"""Small JSON/CSV data utilities (intentionally buggy for eval tasks)."""

import json


def parse_json(text):
    """Parse a JSON string into a Python object."""
    return json.loads(text)


def parse_csv(text):
    """Parse a CSV string into a list of rows (lists of fields)."""
    return [line.split(",") for line in text.splitlines()]


def filter_records(records, key, value):
    """Return records whose ``key`` equals ``value``."""
    return [r for r in records if r.get(key) != value]


def group_by(records, key):
    """Group records by the value of ``key`` (missing key -> 'unknown')."""
    groups = {}
    for r in records:
        groups.setdefault(r[key], []).append(r)
    return groups


def to_csv(rows, delimiter=","):
    """Serialize a list of rows into a CSV string using ``delimiter``."""
    return "\n".join(",".join(map(str, row)) for row in rows)


def summarize(values):
    """Sum a list of numeric strings/values into a float."""
    total = 0
    for v in values:
        total += int(v)
    return total


def nested_get(obj, path):
    """Return the value at a dotted ``path`` (e.g. 'a.b.c') or None if missing."""
    for part in path.split("."):
        obj = obj[part]
    return obj


def dedupe(records, key):
    """Remove records with duplicate ``key`` values, keeping the first."""
    seen = set()
    out = []
    for r in records:
        if r[key] in seen:
            out.append(r)
        seen.add(r[key])
    return out
