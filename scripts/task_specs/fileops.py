"""Repo spec: ``fileops`` — a small, dependency-free file-I/O helper library.

This is a multi-module package: a private ``_open`` helper (shared file handle +
parent-directory management), three functional modules (``read`` / ``write`` /
``csvio``) and a ``scan`` module, plus a public ``__init__`` that re-exports the
API. Bugs range from one-line logic slips and boundary conditions to a resource
leak (a context manager that forgets to close its handle), a hand-rolled CSV
serializer, and cross-file wiring mistakes (a shared helper default and missing
parent-directory creation spread across modules).
"""

REPO = "fileops"

FILES = {
    "fileops/__init__.py": '''"""A small, dependency-free file-I/O helper library.

Public API:
- reading: ``read_lines`` / ``tail`` / ``count_lines``
- writing: ``safe_write`` / ``append_line``
- CSV: ``read_dicts`` / ``write_dicts``
- scanning: ``list_by_extension``
"""

from fileops.csvio import read_dicts, write_dicts
from fileops.read import count_lines, read_lines, tail
from fileops.scan import list_by_extension
from fileops.write import append_line, safe_write

__all__ = [
    "read_lines",
    "tail",
    "count_lines",
    "safe_write",
    "append_line",
    "read_dicts",
    "write_dicts",
    "list_by_extension",
]
''',
    "fileops/_open.py": '''"""Shared file-opening and path helpers (private)."""

from contextlib import contextmanager
from pathlib import Path


@contextmanager
def open_text(path, mode="r", encoding="utf-8", newline=None):
    """Open ``path`` as a text file and yield the handle, closing it on exit."""
    handle = open(path, mode, encoding=encoding, newline=newline)
    try:
        yield handle
    finally:
        handle.close()


def ensure_parent(path):
    """Create the parent directory of ``path`` (if any) and return ``path``."""
    parent = Path(path).parent
    if str(parent) not in ("", "."):
        parent.mkdir(parents=True, exist_ok=True)
    return str(path)
''',
    "fileops/read.py": '''"""Reading text files: whole-file lines, tails, and line counts."""

from fileops._open import open_text


def read_lines(path):
    """Return the lines of ``path`` as strings, with trailing newlines stripped."""
    with open_text(path, "r") as handle:
        return [line.rstrip("\\n") for line in handle]


def tail(path, n):
    """Return the last ``n`` lines of ``path`` (trailing newlines stripped)."""
    with open_text(path, "r") as handle:
        lines = [line.rstrip("\\n") for line in handle]
    return lines[-n:]


def count_lines(path):
    """Return the number of lines in ``path`` (0 for an empty file)."""
    with open_text(path, "r") as handle:
        return sum(1 for _ in handle)
''',
    "fileops/write.py": '''"""Writing text files: whole-file writes and line appends."""

from fileops._open import ensure_parent, open_text


def safe_write(path, content):
    """Write ``content`` to ``path``, creating missing parent directories first."""
    ensure_parent(path)
    with open_text(path, "w", newline="\\n") as handle:
        handle.write(content)
    return str(path)


def append_line(path, line):
    """Append ``line`` plus a newline to ``path``, creating parent directories."""
    ensure_parent(path)
    with open_text(path, "a", newline="\\n") as handle:
        handle.write(line + "\\n")
    return str(path)
''',
    "fileops/csvio.py": '''"""Reading and writing CSV files as lists of dicts."""

import csv

from fileops._open import ensure_parent, open_text


def read_dicts(path):
    """Read a CSV file with a header row into a list of dicts."""
    with open_text(path, "r", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def write_dicts(path, rows, fieldnames=None):
    """Write ``rows`` (a list of dicts) to a CSV file at ``path``.

    Columns follow ``fieldnames`` if given, otherwise the keys of the first
    row. The header row is always written first.
    """
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    ensure_parent(path)
    with open_text(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\\n")
        writer.writeheader()
        writer.writerows(rows)
    return str(path)
''',
    "fileops/scan.py": '''"""Scanning directories for files by extension."""

import os


def list_by_extension(directory, extension):
    """Return a sorted list of file names in ``directory`` matching ``extension``.

    Matching is case-insensitive and ignores a leading dot, so ``".txt"``,
    ``"txt"`` and ``".TXT"`` all match ``report.TXT``.
    """
    ext = extension.lower().lstrip(".")
    names = []
    for name in os.listdir(directory):
        full = os.path.join(directory, name)
        if os.path.isfile(full) and name.lower().endswith("." + ext):
            names.append(name)
    return sorted(names)
''',
}

TESTS = {
    "tests/test_read.py": '''from fileops.read import count_lines, read_lines, tail


def test_read_lines_basic(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\\nb\\nc\\n", encoding="utf-8")
    assert read_lines(path) == ["a", "b", "c"]


def test_read_lines_no_trailing_newline(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\\nb", encoding="utf-8")
    assert read_lines(path) == ["a", "b"]


def test_read_lines_preserves_trailing_spaces(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("hello   \\nworld\\n", encoding="utf-8")
    assert read_lines(path) == ["hello   ", "world"]


def test_read_lines_preserves_trailing_tabs(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("x\\t\\n", encoding="utf-8")
    assert read_lines(path) == ["x\\t"]


def test_read_lines_empty_file(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("", encoding="utf-8")
    assert read_lines(path) == []


def test_read_lines_unicode(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("中文\\nenglish\\n", encoding="utf-8")
    assert read_lines(path) == ["中文", "english"]


def test_tail_last_two(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\\nb\\nc\\nd\\ne\\n", encoding="utf-8")
    assert tail(path, 2) == ["d", "e"]


def test_tail_last_one(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\\nb\\nc\\n", encoding="utf-8")
    assert tail(path, 1) == ["c"]


def test_tail_n_greater_than_file(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\\nb\\nc\\n", encoding="utf-8")
    assert tail(path, 100) == ["a", "b", "c"]


def test_tail_full_file(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\\nb\\nc\\n", encoding="utf-8")
    assert tail(path, 3) == ["a", "b", "c"]


def test_count_lines_basic(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\\nb\\nc\\n", encoding="utf-8")
    assert count_lines(path) == 3


def test_count_lines_no_trailing_newline(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\\nb\\nc", encoding="utf-8")
    assert count_lines(path) == 3


def test_count_lines_empty_file(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("", encoding="utf-8")
    assert count_lines(path) == 0


def test_count_lines_single_line(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("a\\n", encoding="utf-8")
    assert count_lines(path) == 1
''',
    "tests/test_write.py": '''from fileops._open import open_text
from fileops.write import append_line, safe_write


def test_safe_write_basic(tmp_path):
    path = tmp_path / "out.txt"
    safe_write(path, "hello")
    assert path.read_text(encoding="utf-8") == "hello"


def test_safe_write_overwrites(tmp_path):
    path = tmp_path / "out.txt"
    safe_write(path, "first")
    safe_write(path, "second")
    assert path.read_text(encoding="utf-8") == "second"


def test_safe_write_truncates_existing(tmp_path):
    path = tmp_path / "out.txt"
    path.write_text("old content", encoding="utf-8")
    safe_write(path, "new")
    assert path.read_text(encoding="utf-8") == "new"


def test_safe_write_creates_parent_dirs(tmp_path):
    path = tmp_path / "a" / "b" / "out.txt"
    safe_write(path, "nested")
    assert path.read_text(encoding="utf-8") == "nested"


def test_append_line_adds_newline(tmp_path):
    path = tmp_path / "log.txt"
    append_line(path, "hello")
    assert path.read_text(encoding="utf-8") == "hello\\n"


def test_append_line_multiple_lines(tmp_path):
    path = tmp_path / "log.txt"
    append_line(path, "first")
    append_line(path, "second")
    assert path.read_text(encoding="utf-8") == "first\\nsecond\\n"


def test_append_line_creates_file(tmp_path):
    path = tmp_path / "log.txt"
    append_line(path, "entry")
    assert path.exists()
    assert "entry" in path.read_text(encoding="utf-8")


def test_open_text_closes_handle(tmp_path):
    path = tmp_path / "data.txt"
    path.write_text("hello", encoding="utf-8")
    with open_text(path) as handle:
        assert handle.read() == "hello"
        assert handle.closed is False
    assert handle.closed is True


def test_open_text_closes_after_write(tmp_path):
    path = tmp_path / "out.txt"
    with open_text(path, "w") as handle:
        handle.write("hello")
    assert handle.closed is True
''',
    "tests/test_data.py": '''import fileops
from fileops.csvio import read_dicts, write_dicts
from fileops.scan import list_by_extension


def test_read_dicts_multiple_rows(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("name,age\\nalice,30\\nbob,25\\ncarol,40\\n", encoding="utf-8")
    assert read_dicts(path) == [
        {"name": "alice", "age": "30"},
        {"name": "bob", "age": "25"},
        {"name": "carol", "age": "40"},
    ]


def test_read_dicts_header_only(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("name,age\\n", encoding="utf-8")
    assert read_dicts(path) == []


def test_read_dicts_unicode(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("name,城市\\nalice,北京\\n", encoding="utf-8")
    assert read_dicts(path) == [{"name": "alice", "城市": "北京"}]


def test_write_dicts_roundtrip(tmp_path):
    path = tmp_path / "data.csv"
    rows = [
        {"name": "alice", "age": "30"},
        {"name": "bob", "age": "25"},
    ]
    write_dicts(path, rows)
    assert read_dicts(path) == rows


def test_write_dicts_value_with_equals(tmp_path):
    path = tmp_path / "data.csv"
    write_dicts(path, [{"key": "a=b"}])
    assert read_dicts(path) == [{"key": "a=b"}]


def test_write_dicts_creates_file(tmp_path):
    path = tmp_path / "data.csv"
    write_dicts(path, [{"name": "alice"}])
    assert path.exists()
    assert "name" in path.read_text(encoding="utf-8")


def test_write_dicts_creates_parent_dirs(tmp_path):
    path = tmp_path / "x" / "y" / "data.csv"
    write_dicts(path, [{"name": "alice"}])
    assert read_dicts(path) == [{"name": "alice"}]


def test_list_by_extension_basic(tmp_path):
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "b.txt").write_text("2")
    (tmp_path / "c.csv").write_text("3")
    assert list_by_extension(tmp_path, "txt") == ["a.txt", "b.txt"]


def test_list_by_extension_case_insensitive(tmp_path):
    (tmp_path / "report.TXT").write_text("1")
    (tmp_path / "note.txt").write_text("2")
    assert list_by_extension(tmp_path, "txt") == ["note.txt", "report.TXT"]


def test_list_by_extension_leading_dot(tmp_path):
    (tmp_path / "a.txt").write_text("1")
    assert list_by_extension(tmp_path, ".txt") == ["a.txt"]


def test_list_by_extension_skips_directories(tmp_path):
    (tmp_path / "notes.txt").mkdir()
    (tmp_path / "a.txt").write_text("1")
    assert list_by_extension(tmp_path, "txt") == ["a.txt"]


def test_list_by_extension_sorted(tmp_path):
    (tmp_path / "c.txt").write_text("1")
    (tmp_path / "a.txt").write_text("2")
    (tmp_path / "b.txt").write_text("3")
    assert list_by_extension(tmp_path, "txt") == ["a.txt", "b.txt", "c.txt"]


def test_api_all_public_names_present():
    for name in [
        "read_lines",
        "tail",
        "count_lines",
        "safe_write",
        "append_line",
        "read_dicts",
        "write_dicts",
        "list_by_extension",
    ]:
        assert hasattr(fileops, name), f"missing {name}"


def test_api_tail():
    assert callable(fileops.tail)


def test_api_read_lines():
    assert callable(fileops.read_lines)


def test_api_safe_write(tmp_path):
    path = tmp_path / "out.txt"
    fileops.safe_write(path, "hello")
    assert path.read_text(encoding="utf-8") == "hello"


def test_api_list_by_extension(tmp_path):
    (tmp_path / "a.txt").write_text("1")
    assert fileops.list_by_extension(tmp_path, "txt") == ["a.txt"]
''',
}

TASKS = [
    {
        "id": "fileops-01",
        "instruction": (
            "Fix `count_lines` in `fileops/read.py`. A file that ends with a trailing "
            "newline is reported with one line too many (e.g. `\"a\\n\"` -> 2 instead of 1), "
            "and an empty file is reported as having 1 line instead of 0. The count should "
            "reflect the number of lines the file actually contains."
        ),
        "difficulty": "easy",
        "category": "reading",
        "lines": 1,
        "bug": [
            (
                "fileops/read.py",
                '        return sum(1 for _ in handle)',
                '        return len(handle.read().split("\\n"))',
            )
        ],
        "fail_to_pass": [
            "tests/test_read.py::test_count_lines_empty_file",
            "tests/test_read.py::test_count_lines_single_line",
            "tests/test_read.py::test_count_lines_basic",
        ],
        "pass_to_pass": [
            "tests/test_read.py::test_count_lines_no_trailing_newline",
            "tests/test_read.py::test_read_lines_basic",
        ],
    },
    {
        "id": "fileops-02",
        "instruction": (
            "Fix `read_lines` in `fileops/read.py` so it strips only the trailing newline "
            "from each line, not all trailing whitespace. Lines ending in spaces or tabs "
            "(e.g. `\"hello   \"`) currently come back with that whitespace silently removed."
        ),
        "difficulty": "easy",
        "category": "reading",
        "lines": 1,
        "bug": [
            (
                "fileops/read.py",
                '        return [line.rstrip("\\n") for line in handle]',
                '        return [line.rstrip() for line in handle]',
            )
        ],
        "fail_to_pass": [
            "tests/test_read.py::test_read_lines_preserves_trailing_spaces",
            "tests/test_read.py::test_read_lines_preserves_trailing_tabs",
        ],
        "pass_to_pass": [
            "tests/test_read.py::test_read_lines_basic",
            "tests/test_read.py::test_read_lines_no_trailing_newline",
            "tests/test_read.py::test_read_lines_empty_file",
        ],
    },
    {
        "id": "fileops-03",
        "instruction": (
            "Fix `tail` in `fileops/read.py`. It currently returns the FIRST `n` lines of "
            "a file instead of the LAST `n` lines."
        ),
        "difficulty": "easy",
        "category": "reading",
        "lines": 1,
        "bug": [
            (
                "fileops/read.py",
                "    return lines[-n:]",
                "    return lines[:n]",
            )
        ],
        "fail_to_pass": [
            "tests/test_read.py::test_tail_last_two",
            "tests/test_read.py::test_tail_last_one",
        ],
        "pass_to_pass": [
            "tests/test_read.py::test_tail_n_greater_than_file",
            "tests/test_read.py::test_tail_full_file",
        ],
    },
    {
        "id": "fileops-04",
        "instruction": (
            "Fix `append_line` in `fileops/write.py` so each appended line is terminated by "
            "a newline. Appending several lines currently runs them together on a single line."
        ),
        "difficulty": "medium",
        "category": "writing",
        "lines": 1,
        "bug": [
            (
                "fileops/write.py",
                '        handle.write(line + "\\n")',
                "        handle.write(line)",
            )
        ],
        "fail_to_pass": [
            "tests/test_write.py::test_append_line_adds_newline",
            "tests/test_write.py::test_append_line_multiple_lines",
        ],
        "pass_to_pass": [
            "tests/test_write.py::test_append_line_creates_file",
            "tests/test_write.py::test_safe_write_basic",
        ],
    },
    {
        "id": "fileops-05",
        "instruction": (
            "Fix `list_by_extension` in `fileops/scan.py` so the extension match is "
            "case-insensitive. Searching for `\"txt\"` currently misses files whose names "
            "are uppercase (e.g. `report.TXT`)."
        ),
        "difficulty": "easy",
        "category": "scanning",
        "lines": 1,
        "bug": [
            (
                "fileops/scan.py",
                '        if os.path.isfile(full) and name.lower().endswith("." + ext):',
                '        if os.path.isfile(full) and name.endswith("." + ext):',
            )
        ],
        "fail_to_pass": [
            "tests/test_data.py::test_list_by_extension_case_insensitive",
        ],
        "pass_to_pass": [
            "tests/test_data.py::test_list_by_extension_basic",
            "tests/test_data.py::test_list_by_extension_leading_dot",
            "tests/test_data.py::test_list_by_extension_skips_directories",
            "tests/test_data.py::test_list_by_extension_sorted",
        ],
    },
    {
        "id": "fileops-06",
        "instruction": (
            "Fix `read_dicts` in `fileops/csvio.py` so it returns ALL data rows as a list of "
            "dicts, not just the first row. A CSV with several rows currently yields only one "
            "dict, and a header-only CSV crashes."
        ),
        "difficulty": "medium",
        "category": "csv",
        "lines": 1,
        "bug": [
            (
                "fileops/csvio.py",
                "        return list(reader)",
                "        return next(reader)",
            )
        ],
        "fail_to_pass": [
            "tests/test_data.py::test_read_dicts_multiple_rows",
            "tests/test_data.py::test_read_dicts_header_only",
        ],
        "pass_to_pass": [
            "tests/test_data.py::test_list_by_extension_basic",
            "tests/test_write.py::test_safe_write_overwrites",
            "tests/test_read.py::test_count_lines_basic",
        ],
    },
    {
        "id": "fileops-07",
        "instruction": (
            "Fix `write_dicts` in `fileops/csvio.py` so it writes proper CSV using the `csv` "
            "module's `DictWriter`. The current hand-rolled serializer corrupts values "
            "containing `=` and breaks round-tripping through `read_dicts`."
        ),
        "difficulty": "medium",
        "category": "csv",
        "lines": 6,
        "bug": [
            (
                "fileops/csvio.py",
                (
                    '    with open_text(path, "w", newline="") as handle:\n'
                    '        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\\n")\n'
                    "        writer.writeheader()\n"
                    "        writer.writerows(rows)"
                ),
                (
                    '    with open_text(path, "w", newline="\\n") as handle:\n'
                    '        handle.write(",".join(fieldnames) + "\\n")\n'
                    "        for row in rows:\n"
                    '            handle.write(",".join(f"{k}={row.get(k)}" for k in fieldnames) + "\\n")'
                ),
            )
        ],
        "fail_to_pass": [
            "tests/test_data.py::test_write_dicts_roundtrip",
            "tests/test_data.py::test_write_dicts_value_with_equals",
        ],
        "pass_to_pass": [
            "tests/test_data.py::test_write_dicts_creates_file",
            "tests/test_data.py::test_list_by_extension_basic",
            "tests/test_read.py::test_count_lines_no_trailing_newline",
        ],
    },
    {
        "id": "fileops-08",
        "instruction": (
            "Fix `safe_write` in `fileops/write.py` so writing to an existing file replaces "
            "its contents. It currently appends instead of truncating, so a second write "
            "leaves the old content in place."
        ),
        "difficulty": "medium",
        "category": "writing",
        "lines": 1,
        "bug": [
            (
                "fileops/write.py",
                '    with open_text(path, "w", newline="\\n") as handle:\n        handle.write(content)',
                '    with open_text(path, "a", newline="\\n") as handle:\n        handle.write(content)',
            )
        ],
        "fail_to_pass": [
            "tests/test_write.py::test_safe_write_overwrites",
            "tests/test_write.py::test_safe_write_truncates_existing",
        ],
        "pass_to_pass": [
            "tests/test_write.py::test_safe_write_basic",
            "tests/test_write.py::test_safe_write_creates_parent_dirs",
            "tests/test_write.py::test_append_line_adds_newline",
        ],
    },
    {
        "id": "fileops-09",
        "instruction": (
            "Fix `open_text` in `fileops/_open.py` so the file handle it yields is closed "
            "when the context manager exits. The handle currently leaks (stays open) after "
            "the `with` block, so `handle.closed` is `False` afterwards."
        ),
        "difficulty": "medium",
        "category": "resource",
        "lines": 3,
        "bug": [
            (
                "fileops/_open.py",
                "    try:\n        yield handle\n    finally:\n        handle.close()",
                "    yield handle",
            )
        ],
        "fail_to_pass": [
            "tests/test_write.py::test_open_text_closes_handle",
            "tests/test_write.py::test_open_text_closes_after_write",
        ],
        "pass_to_pass": [
            "tests/test_read.py::test_read_lines_basic",
            "tests/test_read.py::test_count_lines_basic",
            "tests/test_data.py::test_list_by_extension_basic",
        ],
    },
    {
        "id": "fileops-10",
        "instruction": (
            "Fix `open_text` in `fileops/_open.py` so it opens files as UTF-8 by default. "
            "The default encoding is currently ASCII, so reading any non-ASCII file through "
            "`read_lines` or `read_dicts` raises `UnicodeDecodeError`."
        ),
        "difficulty": "hard",
        "category": "io",
        "lines": 1,
        "bug": [
            (
                "fileops/_open.py",
                'def open_text(path, mode="r", encoding="utf-8", newline=None):',
                'def open_text(path, mode="r", encoding="ascii", newline=None):',
            )
        ],
        "fail_to_pass": [
            "tests/test_read.py::test_read_lines_unicode",
            "tests/test_data.py::test_read_dicts_unicode",
        ],
        "pass_to_pass": [
            "tests/test_read.py::test_read_lines_basic",
            "tests/test_write.py::test_safe_write_basic",
            "tests/test_data.py::test_list_by_extension_basic",
        ],
    },
    {
        "id": "fileops-11",
        "instruction": (
            "Fix `safe_write` in `fileops/write.py` and `write_dicts` in `fileops/csvio.py` "
            "so they create missing parent directories before opening the file. Writing to a "
            "path whose parent directory does not exist (e.g. `a/b/out.txt`) currently raises "
            "`FileNotFoundError`."
        ),
        "difficulty": "hard",
        "category": "writing",
        "lines": 2,
        "bug": [
            (
                "fileops/write.py",
                '    ensure_parent(path)\n    with open_text(path, "w", newline="\\n") as handle:',
                '    with open_text(path, "w", newline="\\n") as handle:',
            ),
            (
                "fileops/csvio.py",
                '    ensure_parent(path)\n    with open_text(path, "w", newline="") as handle:',
                '    with open_text(path, "w", newline="") as handle:',
            ),
        ],
        "fail_to_pass": [
            "tests/test_write.py::test_safe_write_creates_parent_dirs",
            "tests/test_data.py::test_write_dicts_creates_parent_dirs",
        ],
        "pass_to_pass": [
            "tests/test_write.py::test_safe_write_basic",
            "tests/test_write.py::test_append_line_adds_newline",
            "tests/test_data.py::test_write_dicts_roundtrip",
        ],
    },
    {
        "id": "fileops-12",
        "instruction": (
            "Fix the package's public API in `fileops/__init__.py` so `tail` is exported. "
            "`fileops.tail` is currently missing and callers get an `AttributeError`."
        ),
        "difficulty": "hard",
        "category": "api",
        "lines": 1,
        "bug": [
            (
                "fileops/__init__.py",
                "from fileops.read import count_lines, read_lines, tail",
                "from fileops.read import count_lines, read_lines",
            )
        ],
        "fail_to_pass": [
            "tests/test_data.py::test_api_all_public_names_present",
            "tests/test_data.py::test_api_tail",
        ],
        "pass_to_pass": [
            "tests/test_data.py::test_api_read_lines",
            "tests/test_data.py::test_api_safe_write",
            "tests/test_data.py::test_api_list_by_extension",
        ],
    },
]
