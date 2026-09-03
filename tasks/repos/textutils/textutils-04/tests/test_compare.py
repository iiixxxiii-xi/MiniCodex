from textutils.compare import common_prefix, is_palindrome


def test_is_palindrome_basic():
    assert is_palindrome("racecar") is True


def test_is_palindrome_case_insensitive():
    assert is_palindrome("RaceCar") is True


def test_is_palindrome_ignore_space_punct():
    assert is_palindrome("A man, a plan, a canal: Panama") is True


def test_is_palindrome_ignore_punct():
    assert is_palindrome("Madam, I'm Adam.") is True


def test_is_palindrome_not_palindrome():
    assert is_palindrome("hello") is False


def test_is_palindrome_empty():
    assert is_palindrome("") is True


def test_is_palindrome_single():
    assert is_palindrome("a") is True


def test_common_prefix_basic():
    assert common_prefix("prefix", "preview") == "pre"


def test_common_prefix_no_common():
    assert common_prefix("abc", "xyz") == ""


def test_common_prefix_empty():
    assert common_prefix("", "abc") == ""


def test_common_prefix_full_match():
    assert common_prefix("same", "same") == "same"


def test_common_prefix_one_char():
    assert common_prefix("a", "a") == "a"
