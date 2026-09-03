from textutils.words import capitalize_words, count_vowels, reverse_words


def test_reverse_words_basic():
    assert reverse_words("hello world") == "world hello"


def test_reverse_words_three():
    assert reverse_words("one two three") == "three two one"


def test_reverse_words_single():
    assert reverse_words("hello") == "hello"


def test_reverse_words_empty():
    assert reverse_words("") == ""


def test_reverse_words_multiple_spaces():
    assert reverse_words("a  b   c") == "c b a"


def test_capitalize_words_basic():
    assert capitalize_words("hello world") == "Hello World"


def test_capitalize_words_mixed_case():
    assert capitalize_words("hELLO wORLD") == "Hello World"


def test_capitalize_words_single():
    assert capitalize_words("PYTHON") == "Python"


def test_capitalize_words_multiple_spaces():
    assert capitalize_words("a  b") == "A B"


def test_capitalize_words_empty():
    assert capitalize_words("") == ""


def test_count_vowels_basic():
    assert count_vowels("hello") == 2


def test_count_vowels_uppercase():
    assert count_vowels("HELLO") == 2


def test_count_vowels_aeiou():
    assert count_vowels("AEIOU") == 5


def test_count_vowels_mixed():
    assert count_vowels("Hello World") == 3


def test_count_vowels_no_vowels():
    assert count_vowels("rhythm") == 0


def test_count_vowels_empty():
    assert count_vowels("") == 0


def test_count_vowels_accents_ascii_only():
    assert count_vowels("café") == 1


def test_count_vowels_japanese():
    assert count_vowels("こんにちは") == 0
