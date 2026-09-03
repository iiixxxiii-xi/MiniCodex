from codec.url import decode_query, encode_query, url_decode, url_encode


def test_url_encode_spaces():
    assert url_encode("hello world") == "hello%20world"


def test_url_encode_reserved():
    assert url_encode("a/b") == "a%2Fb"


def test_url_encode_multiple_slashes():
    assert url_encode("a/b/c") == "a%2Fb%2Fc"


def test_url_decode_plus():
    assert url_decode("hello+world") == "hello world"


def test_url_decode_plus_multiple():
    assert url_decode("a+b+c") == "a b c"


def test_url_decode_percent():
    assert url_decode("hello%20world") == "hello world"


def test_encode_query_basic():
    assert encode_query({"a": "b", "c": "d"}) == "a=b&c=d"


def test_encode_query_encodes_key():
    assert encode_query({"a b": "c d"}) == "a%20b=c%20d"


def test_encode_query_encodes_reserved():
    assert encode_query({"a/b": "c"}) == "a%2Fb=c"


def test_encode_query_encodes_value():
    assert encode_query({"x": "a/b"}) == "x=a%2Fb"


def test_decode_query_basic():
    assert decode_query("a=1&b=2") == {"a": ["1"], "b": ["2"]}


def test_decode_query_multi_value():
    assert decode_query("a=1&a=2") == {"a": ["1", "2"]}


def test_decode_query_plus():
    assert decode_query("a=hello+world") == {"a": ["hello world"]}


def test_decode_query_flag():
    assert decode_query("flag") == {"flag": [""]}


def test_decode_query_flag_mixed():
    assert decode_query("a=1&flag") == {"a": ["1"], "flag": [""]}
