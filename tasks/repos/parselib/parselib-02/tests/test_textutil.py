import pytest

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
    assert split_words("a\tb\tc") == ["a", "b", "c"]


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
