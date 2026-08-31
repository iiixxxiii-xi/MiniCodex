import textutils


def test_reverse_words():
    assert textutils.reverse_words("hello world") == "world hello"
    assert textutils.reverse_words("a b c") == "c b a"


def test_capitalize_words():
    assert textutils.capitalize_words("hello world") == "Hello World"
    assert textutils.capitalize_words("hello WORLD") == "Hello WORLD"


def test_count_vowels():
    assert textutils.count_vowels("Hello wOrld") == 3
    assert textutils.count_vowels("aeiou") == 5
    assert textutils.count_vowels("AEIOU") == 5


def test_truncate():
    assert textutils.truncate("hello", 10) == "hello"
    assert textutils.truncate("hello world", 5) == "hello..."


def test_slugify():
    assert textutils.slugify("Hello World") == "hello-world"
    assert textutils.slugify("  Hello   World  ") == "hello-world"


def test_camel_to_snake():
    assert textutils.camel_to_snake("HelloWorld") == "hello_world"
    assert textutils.camel_to_snake("hello") == "hello"


def test_is_palindrome():
    assert textutils.is_palindrome("racecar") is True
    assert textutils.is_palindrome("A man a plan a canal Panama") is True
    assert textutils.is_palindrome("hello") is False


def test_common_prefix():
    assert textutils.common_prefix("abcdef", "abcxyz") == "abc"
    assert textutils.common_prefix("abc", "def") == ""


def test_wrap():
    assert textutils.wrap("abcdef", 3) == "abc\ndef"
    assert textutils.wrap("hello", 10) == "hello"


def test_count_occurrences():
    assert textutils.count_occurrences("aaaa", "aa") == 2
    assert textutils.count_occurrences("hello", "l") == 2
