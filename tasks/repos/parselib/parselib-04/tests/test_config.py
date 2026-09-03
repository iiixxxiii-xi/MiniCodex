from parselib.ini import parse_ini
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
