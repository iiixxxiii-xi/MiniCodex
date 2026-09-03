from codec.text import byte_count, char_count, normalize


def test_char_count_ascii():
    assert char_count("hello") == 5


def test_char_count_unicode():
    assert char_count("中文") == 2


def test_byte_count_ascii():
    assert byte_count("hello") == 5


def test_byte_count_unicode():
    assert byte_count("中") == 3


def test_byte_count_unicode_two():
    assert byte_count("中文") == 6


def test_normalize_composed():
    assert normalize("e\u0301") == "\u00e9"


def test_normalize_composed_two():
    assert normalize("a\u0300") == "\u00e0"


def test_normalize_already_nfc():
    assert normalize("hello") == "hello"
