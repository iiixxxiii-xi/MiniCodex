from textutils.wrapping import count_occurrences, wrap


def test_wrap_no_wrap_needed():
    assert wrap("hello world", 20) == "hello world"


def test_wrap_basic():
    assert wrap("aaa bb cc ddddd", 6) == "aaa bb\ncc\nddddd"


def test_wrap_exact_fit():
    assert wrap("aaa bb", 6) == "aaa bb"


def test_wrap_long_word_unbroken():
    assert wrap("hello", 3) == "hello"


def test_wrap_empty():
    assert wrap("", 5) == ""


def test_wrap_collapses_spaces():
    assert wrap("a  b  c", 100) == "a b c"


def test_count_occurrences_basic():
    assert count_occurrences("hello", "l") == 2


def test_count_occurrences_overlap_nonoverlapping():
    assert count_occurrences("aaaa", "aa") == 2


def test_count_occurrences_banana():
    assert count_occurrences("banana", "ana") == 1


def test_count_occurrences_no_match():
    assert count_occurrences("hello", "x") == 0


def test_count_occurrences_empty_text():
    assert count_occurrences("", "a") == 0


def test_count_occurrences_empty_sub():
    assert count_occurrences("hello", "") == 0
