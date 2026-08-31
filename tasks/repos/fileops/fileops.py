"""Small file I/O helpers (intentionally buggy for eval tasks)."""

import os


def read_lines(path):
    """Read a text file and return its lines without trailing newlines."""
    with open(path, encoding="utf-8") as f:
        return f.read().split()


def count_lines(path):
    """Count the number of lines in a text file."""
    with open(path, encoding="utf-8") as f:
        return len(f.read().split("\n"))


def tail(path, n):
    """Return the last ``n`` lines of a text file."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    return lines[-n:]


def parse_kv(path):
    """Parse a 'key=value' file into a dict."""
    result = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            key, value = line.split("=")
            result[key] = value
    return result


def list_by_extension(directory, extension):
    """Return filenames in ``directory`` ending with ``extension`` (sorted)."""
    return sorted(f for f in os.listdir(directory) if f.endswith(extension))


def safe_write(path, content):
    """Write ``content`` to ``path``, creating the file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def read_csv_as_dicts(path):
    """Read a CSV file with a header row into a list of dicts."""
    import csv
    with open(path, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    return [dict(zip(header, row)) for row in rows]


def append_line(path, line):
    """Append ``line`` (plus a newline) to ``path``."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
