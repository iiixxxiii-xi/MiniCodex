"""Repo spec: ``parselib`` — a small, multi-module text/config parsing library.

The library is a real multi-module package: a line-oriented ``textutil`` helper
module (comment stripping, word splitting, ``key=value`` parsing), an ``ini``
parser that reuses ``parse_kv`` from ``textutil``, a blank-tolerant ``jsonio``
module that reuses ``strip_comments``, a ``csvio`` module built on ``csv.reader``,
and a public ``__init__`` that re-exports the API. Bugs span modules (a broken
``parse_kv`` breaks the INI parser; a broken ``strip_comments`` breaks the JSON
parser) and range from one-line slips to multi-line algorithmic errors, plus
cross-file integration bugs whose gold patch touches two files.
"""

REPO = "parselib"

FILES = {
    "parselib/__init__.py": '''"""A small text/config parsing library.

Public API:
- ``jsonio``: blank-tolerant JSON parsing (``load_json``)
- ``csvio``: CSV parsing honouring quoted fields (``parse_csv``)
- ``textutil``: line helpers + ``key=value`` parsing (``strip_comments``,
  ``split_words``, ``parse_kv``)
- ``ini``: INI-style config parsing (``parse_ini``)
"""

from parselib.csvio import parse_csv
from parselib.ini import parse_ini
from parselib.jsonio import load_json
from parselib.textutil import parse_kv, split_words, strip_comments

__all__ = [
    "parse_csv",
    "parse_ini",
    "load_json",
    "parse_kv",
    "split_words",
    "strip_comments",
]
''',
    "parselib/textutil.py": '''"""Line-oriented text helpers and ``key=value`` parsing."""


def strip_comments(line: str) -> str:
    """Remove an inline comment (everything from the first ``#`` or ``;``).

    Returns the line with trailing whitespace stripped. A line with no comment
    marker is returned with only its trailing whitespace stripped.
    """
    positions = [line.find(marker) for marker in ("#", ";")]
    positions = [p for p in positions if p != -1]
    if not positions:
        return line.rstrip()
    return line[:min(positions)].rstrip()


def split_words(text: str) -> list[str]:
    """Split ``text`` into words on runs of whitespace.

    ``"a  b"`` -> ``["a", "b"]``; never emits empty tokens for leading,
    trailing, or repeated whitespace.
    """
    return text.split()


def parse_kv(line: str, sep: str = "=") -> tuple[str, str] | None:
    """Parse one ``key sep value`` line into a ``(key, value)`` tuple.

    Leading/trailing whitespace and inline comments are ignored. Blank or
    comment-only lines return ``None``. Only the first ``sep`` splits, so the
    value may itself contain the separator (``"url=a=b"`` -> ``("url", "a=b")``).
    A line containing neither ``sep`` nor a value raises ``ValueError``.
    """
    cleaned = strip_comments(line).strip()
    if not cleaned:
        return None
    if sep not in cleaned:
        raise ValueError(f"line has no '{sep}' separator: {line!r}")
    key, value = cleaned.split(sep, 1)
    return key.strip(), value.strip()
''',
    "parselib/ini.py": '''"""INI-style config parsing with ``[section]`` headers and top-level keys."""

from parselib.textutil import parse_kv


def parse_ini(text: str) -> dict:
    """Parse INI ``text`` into a nested dict.

    Lines before the first ``[section]`` header are collected as top-level keys.
    Each ``[section]`` begins a nested dict; repeated section headers merge into
    the same dict. ``key = value`` pairs use the same syntax as
    :func:`parselib.textutil.parse_kv`. Blank lines and ``#``/``;`` comments are
    ignored.
    """
    result: dict = {}
    section = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            result.setdefault(section, {})
            continue
        pair = parse_kv(line)
        if pair is None:
            continue
        key, value = pair
        target = result if section is None else result[section]
        target[key] = value
    return result
''',
    "parselib/csvio.py": '''"""CSV parsing that honours quoted fields via the stdlib ``csv`` module."""

import csv
import io


def parse_csv(text: str) -> list[list[str]]:
    """Parse CSV ``text`` into a list of rows (each a list of field strings).

    Quoted fields (``"..."``) may contain commas, double quotes, and newlines;
    the standard ``csv.reader`` handles them. Blank lines are skipped.
    """
    reader = csv.reader(io.StringIO(text))
    return [row for row in reader if row]
''',
    "parselib/jsonio.py": '''"""Blank-tolerant JSON parsing built on the stdlib ``json`` module."""

import json

from parselib.textutil import strip_comments


def load_json(text: str):
    """Parse JSON ``text`` that may contain blank lines and ``#``/``;`` comments.

    Comments are stripped per line before parsing, and surrounding whitespace
    (including leading/trailing blank lines) is ignored.
    """
    cleaned = "\\n".join(strip_comments(line) for line in text.splitlines())
    return json.loads(cleaned)
''',
}

TESTS = {
    "tests/test_textutil.py": '''import pytest

from parselib.textutil import parse_kv, split_words, strip_comments


def test_strip_comments_hash():
    assert strip_comments("key = value  # note") == "key = value"


def test_strip_comments_semicolon():
    assert strip_comments("key = value ; note") == "key = value"


def test_strip_comments_earliest_marker():
    assert strip_comments("a ; hash # later") == "a"


def test_strip_comments_no_marker():
    assert strip_comments("key = value") == "key = value"


def test_strip_comments_only_comment():
    assert strip_comments("# just a comment") == ""


def test_strip_comments_blank():
    assert strip_comments("   ") == ""


def test_split_words_basic():
    assert split_words("a b c") == ["a", "b", "c"]


def test_split_words_multiple_spaces():
    assert split_words("a  b   c") == ["a", "b", "c"]


def test_split_words_tabs():
    assert split_words("a\\tb\\tc") == ["a", "b", "c"]


def test_split_words_leading_trailing():
    assert split_words("  hello world  ") == ["hello", "world"]


def test_split_words_blank():
    assert split_words("   ") == []


def test_parse_kv_basic():
    assert parse_kv("name = alice") == ("name", "alice")


def test_parse_kv_no_spaces():
    assert parse_kv("name=alice") == ("name", "alice")


def test_parse_kv_strips_whitespace():
    assert parse_kv("  key   =   value  ") == ("key", "value")


def test_parse_kv_value_contains_sep():
    assert parse_kv("url = a=b=c") == ("url", "a=b=c")


def test_parse_kv_strips_comment():
    assert parse_kv("port = 8080 # default") == ("port", "8080")


def test_parse_kv_blank():
    assert parse_kv("   ") is None


def test_parse_kv_comment_only():
    assert parse_kv("# comment") is None


def test_parse_kv_missing_sep():
    with pytest.raises(ValueError):
        parse_kv("just_a_word")
''',
    "tests/test_config.py": '''from parselib.ini import parse_ini
from parselib.jsonio import load_json


# --- parse_ini ---

def test_ini_top_level_key():
    assert parse_ini("name = top") == {"name": "top"}


def test_ini_single_section():
    text = """[server]
host = localhost
port = 8080
"""
    assert parse_ini(text) == {"server": {"host": "localhost", "port": "8080"}}


def test_ini_top_level_and_section():
    text = """name = top
[db]
name = inner
"""
    assert parse_ini(text) == {"name": "top", "db": {"name": "inner"}}


def test_ini_multiple_sections():
    text = """[a]
x = 1
[b]
y = 2
"""
    assert parse_ini(text) == {"a": {"x": "1"}, "b": {"y": "2"}}


def test_ini_repeated_section_merges():
    text = """[db]
host = localhost
[app]
name = x
[db]
port = 5432
"""
    assert parse_ini(text) == {"db": {"host": "localhost", "port": "5432"}, "app": {"name": "x"}}


def test_ini_ignores_blank_and_comments():
    text = """# top comment

[db]
; inline
host = localhost  # comment
"""
    assert parse_ini(text) == {"db": {"host": "localhost"}}


def test_ini_section_name_stripped():
    text = """[ db ]
host = localhost
"""
    assert parse_ini(text) == {"db": {"host": "localhost"}}


def test_ini_value_contains_sep():
    text = """[db]
url = a=b=c
"""
    assert parse_ini(text) == {"db": {"url": "a=b=c"}}


def test_ini_duplicate_key_last_wins():
    text = """[db]
host = first
host = second
"""
    assert parse_ini(text) == {"db": {"host": "second"}}


# --- load_json ---

def test_json_basic():
    assert load_json('{"a": 1}') == {"a": 1}


def test_json_blank_lines():
    text = """{

  "a": 1,

  "b": 2
}
"""
    assert load_json(text) == {"a": 1, "b": 2}


def test_json_with_comments():
    text = """# leading
{
  "a": 1,  # inline
  "b": 2
}
"""
    assert load_json(text) == {"a": 1, "b": 2}


def test_json_with_semicolon_comments():
    text = """{
  "a": 1,  ; inline
  "b": 2
}
"""
    assert load_json(text) == {"a": 1, "b": 2}


def test_json_nested():
    assert load_json('{"a": {"b": [1, 2, 3]}}') == {"a": {"b": [1, 2, 3]}}
''',
    "tests/test_csvio.py": '''from parselib.csvio import parse_csv


def test_csv_basic():
    assert parse_csv("a,b,c\\n1,2,3\\n") == [["a", "b", "c"], ["1", "2", "3"]]


def test_csv_quoted_comma():
    assert parse_csv('a,"b,c",d\\n') == [["a", "b,c", "d"]]


def test_csv_quoted_newline():
    assert parse_csv('a,"line1\\nline2",b\\n') == [["a", "line1\\nline2", "b"]]


def test_csv_quoted_quote():
    assert parse_csv('a,"say ""hi""",b\\n') == [["a", 'say "hi"', "b"]]


def test_csv_empty_field():
    assert parse_csv("a,,c\\n") == [["a", "", "c"]]


def test_csv_blank_lines_skipped():
    assert parse_csv("a,b\\n\\n\\nc,d\\n") == [["a", "b"], ["c", "d"]]


def test_csv_single_column():
    assert parse_csv("x\\ny\\nz\\n") == [["x"], ["y"], ["z"]]
''',
    "tests/test_api.py": '''import parselib


def test_api_exports_parsers():
    for name in ["parse_ini", "parse_csv", "parse_kv", "load_json", "strip_comments", "split_words"]:
        assert hasattr(parselib, name), f"missing {name}"


def test_api_json_roundtrip():
    assert parselib.load_json('{"x": 1}') == {"x": 1}


def test_api_kv_roundtrip():
    assert parselib.parse_kv("a = b") == ("a", "b")


def test_api_csv_roundtrip():
    assert parselib.parse_csv("a,b\\n") == [["a", "b"]]


def test_api_ini_roundtrip():
    assert parselib.parse_ini("[s]\\na = 1\\n") == {"s": {"a": "1"}}
''',
}

TASKS = [
    {
        "id": "parselib-01",
        "instruction": (
            "Fix `split_words` in `parselib/textutil.py` so it splits on runs of any "
            "whitespace, not single spaces. The current code uses `str.split(\" \")`, so "
            "tabs and repeated/leading/trailing spaces produce empty tokens or fail to "
            "split at all."
        ),
        "difficulty": "easy",
        "category": "text",
        "lines": 1,
        "bug": [
            (
                "parselib/textutil.py",
                "    return text.split()",
                '    return text.split(" ")',
            )
        ],
        "fail_to_pass": [
            "tests/test_textutil.py::test_split_words_multiple_spaces",
            "tests/test_textutil.py::test_split_words_tabs",
            "tests/test_textutil.py::test_split_words_leading_trailing",
            "tests/test_textutil.py::test_split_words_blank",
        ],
        "pass_to_pass": [
            "tests/test_textutil.py::test_split_words_basic",
            "tests/test_textutil.py::test_strip_comments_hash",
            "tests/test_textutil.py::test_parse_kv_basic",
        ],
    },
    {
        "id": "parselib-02",
        "instruction": (
            "Fix `strip_comments` in `parselib/textutil.py` so it strips trailing "
            "whitespace after removing an inline comment. The current code returns the "
            "truncated line without `.rstrip()`, so callers receive trailing spaces."
        ),
        "difficulty": "easy",
        "category": "text",
        "lines": 1,
        "bug": [
            (
                "parselib/textutil.py",
                "    return line[:min(positions)].rstrip()",
                "    return line[:min(positions)]",
            )
        ],
        "fail_to_pass": [
            "tests/test_textutil.py::test_strip_comments_hash",
            "tests/test_textutil.py::test_strip_comments_earliest_marker",
            "tests/test_textutil.py::test_strip_comments_semicolon",
        ],
        "pass_to_pass": [
            "tests/test_textutil.py::test_strip_comments_no_marker",
            "tests/test_textutil.py::test_strip_comments_only_comment",
            "tests/test_textutil.py::test_strip_comments_blank",
            "tests/test_textutil.py::test_split_words_basic",
        ],
    },
    {
        "id": "parselib-03",
        "instruction": (
            "Fix `parse_kv` in `parselib/textutil.py` so only the *first* separator "
            "splits the line. The current code calls `split(sep)` without a maxsplit, so "
            "a value that itself contains '=' (e.g. `url = a=b=c`) raises a ValueError "
            "instead of returning `(\"url\", \"a=b=c\")`."
        ),
        "difficulty": "easy",
        "category": "kv",
        "lines": 1,
        "bug": [
            (
                "parselib/textutil.py",
                "    key, value = cleaned.split(sep, 1)",
                "    key, value = cleaned.split(sep)",
            )
        ],
        "fail_to_pass": [
            "tests/test_textutil.py::test_parse_kv_value_contains_sep",
            "tests/test_config.py::test_ini_value_contains_sep",
        ],
        "pass_to_pass": [
            "tests/test_textutil.py::test_parse_kv_basic",
            "tests/test_textutil.py::test_parse_kv_no_spaces",
            "tests/test_textutil.py::test_parse_kv_strips_whitespace",
        ],
    },
    {
        "id": "parselib-04",
        "instruction": (
            "Fix `parse_kv` in `parselib/textutil.py` so it strips inline comments "
            "before parsing. The current code strips only surrounding whitespace, so a "
            "line like `port = 8080 # default` keeps the comment as part of the value, "
            "and a comment-only line is not recognised as empty."
        ),
        "difficulty": "easy",
        "category": "kv",
        "lines": 1,
        "bug": [
            (
                "parselib/textutil.py",
                "    cleaned = strip_comments(line).strip()",
                "    cleaned = line.strip()",
            )
        ],
        "fail_to_pass": [
            "tests/test_textutil.py::test_parse_kv_strips_comment",
            "tests/test_textutil.py::test_parse_kv_comment_only",
        ],
        "pass_to_pass": [
            "tests/test_textutil.py::test_parse_kv_basic",
            "tests/test_textutil.py::test_parse_kv_blank",
            "tests/test_textutil.py::test_parse_kv_missing_sep",
        ],
    },
    {
        "id": "parselib-05",
        "instruction": (
            "Fix `load_json` in `parselib/jsonio.py` so it strips ``#``/``;`` comments "
            "before parsing. The current code passes the raw text straight to "
            "`json.loads`, which rejects comment lines and inline comments, so blank-"
            "tolerant JSON with comments fails to parse."
        ),
        "difficulty": "medium",
        "category": "json",
        "lines": 1,
        "bug": [
            (
                "parselib/jsonio.py",
                '    cleaned = "\\n".join(strip_comments(line) for line in text.splitlines())',
                "    cleaned = text",
            )
        ],
        "fail_to_pass": [
            "tests/test_config.py::test_json_with_comments",
            "tests/test_config.py::test_json_with_semicolon_comments",
        ],
        "pass_to_pass": [
            "tests/test_config.py::test_json_basic",
            "tests/test_config.py::test_json_blank_lines",
            "tests/test_config.py::test_json_nested",
        ],
    },
    {
        "id": "parselib-06",
        "instruction": (
            "Fix `parse_csv` in `parselib/csvio.py` so it honours quoted fields via "
            "`csv.reader`. The current code splits each line on ',' with "
            "`line.split(\",\")`, so a quoted field containing a comma, a newline, or an "
            "escaped quote is split into the wrong columns."
        ),
        "difficulty": "medium",
        "category": "csv",
        "lines": 2,
        "bug": [
            (
                "parselib/csvio.py",
                (
                    "    reader = csv.reader(io.StringIO(text))\n"
                    "    return [row for row in reader if row]"
                ),
                '    return [line.split(",") for line in text.splitlines() if line]',
            )
        ],
        "fail_to_pass": [
            "tests/test_csvio.py::test_csv_quoted_comma",
            "tests/test_csvio.py::test_csv_quoted_newline",
            "tests/test_csvio.py::test_csv_quoted_quote",
        ],
        "pass_to_pass": [
            "tests/test_csvio.py::test_csv_basic",
            "tests/test_csvio.py::test_csv_empty_field",
            "tests/test_csvio.py::test_csv_blank_lines_skipped",
            "tests/test_csvio.py::test_csv_single_column",
        ],
    },
    {
        "id": "parselib-07",
        "instruction": (
            "Fix `parse_ini` in `parselib/ini.py` so a repeated key in the same section "
            "keeps the *last* value. The current code uses `dict.setdefault`, so the "
            "first occurrence wins and later duplicate keys are silently ignored."
        ),
        "difficulty": "medium",
        "category": "ini",
        "lines": 1,
        "bug": [
            (
                "parselib/ini.py",
                "        target[key] = value",
                "        target.setdefault(key, value)",
            )
        ],
        "fail_to_pass": [
            "tests/test_config.py::test_ini_duplicate_key_last_wins",
        ],
        "pass_to_pass": [
            "tests/test_config.py::test_ini_single_section",
            "tests/test_config.py::test_ini_top_level_key",
        ],
    },
    {
        "id": "parselib-08",
        "instruction": (
            "Fix `parse_ini` in `parselib/ini.py` so keys are stored under their section "
            "instead of being flattened into the top level. The current code always "
            "writes `result[key]`, so section keys and top-level keys collide and "
            "section headers are effectively ignored."
        ),
        "difficulty": "medium",
        "category": "ini",
        "lines": 2,
        "bug": [
            (
                "parselib/ini.py",
                (
                    "        target = result if section is None else result[section]\n"
                    "        target[key] = value"
                ),
                "        result[key] = value",
            )
        ],
        "fail_to_pass": [
            "tests/test_config.py::test_ini_single_section",
            "tests/test_config.py::test_ini_top_level_and_section",
            "tests/test_config.py::test_ini_multiple_sections",
        ],
        "pass_to_pass": [
            "tests/test_config.py::test_ini_top_level_key",
            "tests/test_config.py::test_json_basic",
        ],
    },
    {
        "id": "parselib-09",
        "instruction": (
            "Fix the package's public API in `parselib/__init__.py` so `parse_ini` is "
            "exported. The `__init__` module currently forgets to import `parse_ini` "
            "from `parselib.ini`, so `parselib.parse_ini` is missing and callers get an "
            "`AttributeError`."
        ),
        "difficulty": "medium",
        "category": "api",
        "lines": 1,
        "bug": [
            (
                "parselib/__init__.py",
                "from parselib.ini import parse_ini",
                "",
            )
        ],
        "fail_to_pass": [
            "tests/test_api.py::test_api_exports_parsers",
            "tests/test_api.py::test_api_ini_roundtrip",
        ],
        "pass_to_pass": [
            "tests/test_api.py::test_api_json_roundtrip",
            "tests/test_api.py::test_api_kv_roundtrip",
            "tests/test_api.py::test_api_csv_roundtrip",
        ],
    },
    {
        "id": "parselib-10",
        "instruction": (
            "Fix `parse_ini` in `parselib/ini.py` so a repeated section header merges "
            "into the existing section instead of wiping it. The current code assigns a "
            "fresh empty dict each time a section header appears, so keys defined before "
            "a second `[section]` header are lost."
        ),
        "difficulty": "hard",
        "category": "ini",
        "lines": 1,
        "bug": [
            (
                "parselib/ini.py",
                "            result.setdefault(section, {})",
                "            result[section] = {}",
            )
        ],
        "fail_to_pass": [
            "tests/test_config.py::test_ini_repeated_section_merges",
        ],
        "pass_to_pass": [
            "tests/test_config.py::test_ini_single_section",
            "tests/test_config.py::test_ini_multiple_sections",
            "tests/test_config.py::test_ini_top_level_and_section",
        ],
    },
    {
        "id": "parselib-11",
        "instruction": (
            "Semicolon comments are no longer recognised anywhere in the library. In "
            "`parselib/textutil.py` the `strip_comments` helper only looks for ``#``, and "
            "in `parselib/ini.py` the comment-only-line skip only checks for ``#`` as "
            "well. Restore ``;`` support in both places so `strip_comments` and "
            "`parse_ini` handle ``;`` comments correctly."
        ),
        "difficulty": "hard",
        "category": "integration",
        "lines": 2,
        "bug": [
            (
                "parselib/textutil.py",
                '    positions = [line.find(marker) for marker in ("#", ";")]',
                '    positions = [line.find(marker) for marker in ("#",)]',
            ),
            (
                "parselib/ini.py",
                '        if not line or line.startswith(("#", ";")):',
                '        if not line or line.startswith(("#",)):',
            ),
        ],
        "fail_to_pass": [
            "tests/test_textutil.py::test_strip_comments_semicolon",
            "tests/test_config.py::test_ini_ignores_blank_and_comments",
        ],
        "pass_to_pass": [
            "tests/test_textutil.py::test_strip_comments_hash",
            "tests/test_config.py::test_ini_single_section",
            "tests/test_config.py::test_json_basic",
        ],
    },
    {
        "id": "parselib-12",
        "instruction": (
            "Whitespace is no longer being stripped around keys, values, and section "
            "names. In `parselib/textutil.py` the `parse_kv` helper returns the raw key "
            "and value without `.strip()`, and in `parselib/ini.py` the section name is "
            "read without stripping its surrounding whitespace. Restore whitespace "
            "stripping in both places."
        ),
        "difficulty": "hard",
        "category": "integration",
        "lines": 2,
        "bug": [
            (
                "parselib/textutil.py",
                "    return key.strip(), value.strip()",
                "    return key, value",
            ),
            (
                "parselib/ini.py",
                "            section = line[1:-1].strip()",
                "            section = line[1:-1]",
            ),
        ],
        "fail_to_pass": [
            "tests/test_textutil.py::test_parse_kv_strips_whitespace",
            "tests/test_config.py::test_ini_section_name_stripped",
        ],
        "pass_to_pass": [
            "tests/test_textutil.py::test_parse_kv_no_spaces",
            "tests/test_config.py::test_json_basic",
            "tests/test_csvio.py::test_csv_basic",
            "tests/test_textutil.py::test_split_words_basic",
        ],
    },
]
