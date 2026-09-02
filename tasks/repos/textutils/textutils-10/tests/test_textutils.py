import textutils


def test_reverse_words_two():
    assert textutils.reverse_words("hello world") == "world hello"


def test_reverse_words_three():
    assert textutils.reverse_words("a b c") == "c b a"


def test_reverse_words_single():
    assert textutils.reverse_words("single") == "single"


def test_capitalize_words_mixed():
    assert textutils.capitalize_words("hello WORLD") == "Hello WORLD"


def test_capitalize_words_camel():
    assert textutils.capitalize_words("fooBar baz") == "FooBar Baz"


def test_capitalize_words_simple():
    assert textutils.capitalize_words("hello world") == "Hello World"


def test_count_vowels_mixed():
    assert textutils.count_vowels("Hello wOrld") == 3


def test_count_vowels_upper():
    assert textutils.count_vowels("AEIOU") == 5


def test_count_vowels_lower():
    assert textutils.count_vowels("aeiou") == 5


def test_truncate_short():
    assert textutils.truncate("hello", 10) == "hello"


def test_truncate_exact():
    assert textutils.truncate("hello", 5) == "hello"


def test_truncate_long():
    assert textutils.truncate("hello world", 5) == "hello..."


def test_slugify_collapse():
    assert textutils.slugify("  Hello   World  ") == "hello-world"


def test_slugify_tab():
    assert textutils.slugify("a\tb") == "a-b"


def test_slugify_simple():
    assert textutils.slugify("Hello World") == "hello-world"


def test_camel_to_snake_multi():
    assert textutils.camel_to_snake("HelloWorld") == "hello_world"


def test_camel_to_snake_single_upper():
    assert textutils.camel_to_snake("Hello") == "hello"


def test_camel_to_snake_lower():
    assert textutils.camel_to_snake("hello") == "hello"


def test_is_palindrome_case_space():
    assert textutils.is_palindrome("A man a plan a canal Panama") is True


def test_is_palindrome_space():
    assert textutils.is_palindrome("race car") is True


def test_is_palindrome_plain():
    assert textutils.is_palindrome("racecar") is True
    assert textutils.is_palindrome("hello") is False


def test_common_prefix_basic():
    assert textutils.common_prefix("abcdef", "abcxyz") == "abc"


def test_common_prefix_full():
    assert textutils.common_prefix("abc", "abc") == "abc"


def test_common_prefix_none():
    assert textutils.common_prefix("abc", "def") == ""


def test_wrap_basic():
    assert textutils.wrap("abcdef", 3) == "abc\ndef"


def test_wrap_exact_width():
    assert textutils.wrap("hello", 5) == "hello"


def test_wrap_short():
    assert textutils.wrap("hello", 10) == "hello"


def test_count_occurrences_overlap():
    assert textutils.count_occurrences("aaaa", "aa") == 2


def test_count_occurrences_empty_sub():
    assert textutils.count_occurrences("hello", "") == 0


def test_count_occurrences_single():
    assert textutils.count_occurrences("hello", "l") == 2
