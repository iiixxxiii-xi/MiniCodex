import textutils


def test_api_reverse_words():
    assert textutils.reverse_words("hello world") == "world hello"


def test_api_slugify():
    assert textutils.slugify("Hello World") == "hello-world"


def test_api_is_palindrome():
    assert textutils.is_palindrome("A man, a plan, a canal: Panama") is True


def test_api_wrap():
    assert textutils.wrap("a b", 1) == "a\nb"


def test_api_count_vowels():
    assert textutils.count_vowels("AEIOU") == 5


def test_api_all_public_names_present():
    for name in [
        "reverse_words",
        "capitalize_words",
        "count_vowels",
        "slugify",
        "camel_to_snake",
        "is_palindrome",
        "common_prefix",
        "wrap",
        "count_occurrences",
    ]:
        assert hasattr(textutils, name), f"missing {name}"
