import codec


def test_base64_encode_basic():
    assert codec.base64_encode("hello") == "aGVsbG8="


def test_base64_encode_roundtrip():
    assert codec.base64_decode(codec.base64_encode("hello world")) == "hello world"


def test_base64_decode_basic():
    assert codec.base64_decode("aGVsbG8=") == "hello"


def test_hex_encode_basic():
    assert codec.hex_encode("AB") == "4142"


def test_hex_decode_basic():
    assert codec.hex_decode("4142") == "AB"


def test_hex_roundtrip_unicode():
    assert codec.hex_decode(codec.hex_encode("\u4e2d")) == "\u4e2d"


def test_url_encode_spaces():
    assert codec.url_encode("hello world") == "hello%20world"


def test_url_encode_reserved():
    assert codec.url_encode("a/b") == "a%2Fb"


def test_url_encode_multiple_slashes():
    assert codec.url_encode("a/b/c") == "a%2Fb%2Fc"


def test_url_decode_plus():
    assert codec.url_decode("hello+world") == "hello world"


def test_url_decode_plus_multiple():
    assert codec.url_decode("a+b+c") == "a b c"


def test_url_decode_percent():
    assert codec.url_decode("hello%20world") == "hello world"


def test_char_count_ascii():
    assert codec.char_count("hello") == 5


def test_char_count_unicode():
    assert codec.char_count("\u4e2d\u6587") == 2


def test_byte_count_ascii():
    assert codec.byte_count("hello") == 5


def test_byte_count_unicode():
    assert codec.byte_count("\u4e2d") == 3


def test_byte_count_unicode_two():
    assert codec.byte_count("\u4e2d\u6587") == 6


def test_normalize_composed():
    assert codec.normalize("e\u0301") == "\u00e9"


def test_normalize_composed_two():
    assert codec.normalize("a\u0300") == "\u00e0"


def test_normalize_already_nfc():
    assert codec.normalize("hello") == "hello"
