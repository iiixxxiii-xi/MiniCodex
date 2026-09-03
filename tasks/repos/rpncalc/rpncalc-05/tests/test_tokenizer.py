from rpncalc.tokenizer import is_number, parse_number, tokenize


def test_tokenize_basic():
    assert tokenize("3 4 +") == ["3", "4", "+"]


def test_tokenize_single():
    assert tokenize("42") == ["42"]


def test_tokenize_empty():
    assert tokenize("") == []


def test_tokenize_extra_whitespace():
    assert tokenize("  3   4   +  ") == ["3", "4", "+"]


def test_tokenize_whitespace_mixed():
    assert tokenize("3\t4\n+") == ["3", "4", "+"]


def test_is_number_int():
    assert is_number("42") is True


def test_is_number_float():
    assert is_number("3.5") is True


def test_is_number_negative():
    assert is_number("-7") is True


def test_is_number_operator():
    assert is_number("+") is False


def test_is_number_non_numeric():
    assert is_number("abc") is False


def test_parse_number_int():
    assert parse_number("42") == 42


def test_parse_number_float():
    assert parse_number("3.5") == 3.5


def test_parse_number_negative():
    assert parse_number("-7") == -7
