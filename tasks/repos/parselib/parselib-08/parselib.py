"""Small text/config parsing utilities (intentionally buggy for eval tasks)."""

import csv
import io
import json


def parse_json(text):
    """Parse a JSON string, treating blank input as an empty dict."""
    if not text.strip():
        return {}
    return json.loads(text)


def strip_comments(text):
    """Remove `#` line comments from a text block."""
    out = []
    for line in text.splitlines():
        out.append(line.split("#", 1)[0].rstrip())
    return "\n".join(out)


def parse_csv(text):
    """Parse a CSV string into a list of rows (honouring quoted fields)."""
    return [row for row in csv.reader(io.StringIO(text))]


def parse_kv(text):
    """Parse 'key=value' lines into a dict (last occurrence of a key wins)."""
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def parse_ini(text):
    """Parse an INI-style text into nested dicts by [section]."""
    result = {}
    current = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            result[current] = {}
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if current is not None:
            result[current][key.strip()] = value.strip()
        else:
            result[key.strip()] = value.strip()
    return result


def sum_column(rows, idx):
    """Sum the numeric values in column ``idx`` of ``rows``."""
    total = 0.0
    for row in rows:
        total += float(row[idx])
    return total


def get_field(record, key, default=None):
    """Return ``record[key]`` or ``default`` when the key is missing."""
    return record.get(key, default)


def split_words(text):
    """Split ``text`` on whitespace into words."""
    return text.split(" ")
