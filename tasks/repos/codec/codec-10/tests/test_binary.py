from codec.binary import base64_decode, base64_encode, hex_decode, hex_encode


def test_base64_encode_basic():
    assert base64_encode("hello") == "aGVsbG8="


def test_base64_encode_roundtrip():
    assert base64_decode(base64_encode("hello world")) == "hello world"


def test_base64_encode_unicode():
    assert base64_encode("中") == "5Lit"


def test_base64_decode_basic():
    assert base64_decode("aGVsbG8=") == "hello"


def test_base64_decode_unicode():
    assert base64_decode("5Lit") == "中"


def test_hex_encode_basic():
    assert hex_encode("AB") == "4142"


def test_hex_decode_basic():
    assert hex_decode("4142") == "AB"


def test_hex_roundtrip_unicode():
    assert hex_decode(hex_encode("中")) == "中"
