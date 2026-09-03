import codec


def test_api_exports_base64():
    assert callable(codec.base64_encode)
    assert callable(codec.base64_decode)


def test_api_hex_roundtrip():
    assert codec.hex_decode(codec.hex_encode("AB")) == "AB"


def test_api_url_roundtrip():
    assert codec.url_decode(codec.url_encode("a b")) == "a b"


def test_api_byte_count_unicode():
    assert codec.byte_count("中") == 3


def test_api_all_public_names_present():
    for name in [
        "base64_encode",
        "base64_decode",
        "hex_encode",
        "hex_decode",
        "url_encode",
        "url_decode",
        "encode_query",
        "char_count",
        "byte_count",
        "normalize",
    ]:
        assert hasattr(codec, name), f"missing {name}"
