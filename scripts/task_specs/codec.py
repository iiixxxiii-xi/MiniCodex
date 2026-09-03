"""Repo spec: ``codec`` — a small, multi-module encoding/decoding library.

This is the reference spec for the repo-level task set. The library is a real
multi-module package: a private ``_bytes`` helper, three functional modules
(``binary`` / ``url`` / ``text``), and a public ``__init__`` that re-exports the
API. Bugs span modules (e.g. a broken ``_bytes`` helper that breaks ``binary``
and ``text``) and range from one-line type/logic slips to multi-line algorithmic
errors, in addition to cross-file API wiring mistakes.
"""

REPO = "codec"

FILES = {
    "codec/__init__.py": '''"""A small, dependency-free encoding/decoding library.

Public API:
- binary codecs: ``base64_encode`` / ``base64_decode``, ``hex_encode`` / ``hex_decode``
- URL form codecs: ``url_encode`` / ``url_decode`` / ``encode_query``
- text metrics + normalization: ``char_count`` / ``byte_count`` / ``normalize``
"""

from codec.binary import base64_decode, base64_encode, hex_decode, hex_encode
from codec.text import byte_count, char_count, normalize
from codec.url import encode_query, url_decode, url_encode

__all__ = [
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
]
''',
    "codec/_bytes.py": '''"""Shared str <-> bytes conversion helpers (private)."""


def to_bytes(text: str) -> bytes:
    """Encode ``text`` to its UTF-8 bytes."""
    return text.encode("utf-8")


def from_bytes(data: bytes) -> str:
    """Decode UTF-8 ``data`` back into a string."""
    return data.decode("utf-8")
''',
    "codec/binary.py": '''"""Binary text codecs: base64 and hexadecimal."""

import base64

from codec._bytes import from_bytes, to_bytes


def base64_encode(data: str) -> str:
    """Base64-encode ``data`` and return the ASCII text."""
    return base64.b64encode(to_bytes(data)).decode("ascii")


def base64_decode(text: str) -> str:
    """Decode base64 ``text`` back into a UTF-8 string."""
    return from_bytes(base64.b64decode(text))


def hex_encode(data: str) -> str:
    """Hex-encode ``data``'s UTF-8 bytes."""
    return to_bytes(data).hex()


def hex_decode(text: str) -> str:
    """Decode a hex string back into a UTF-8 string."""
    return from_bytes(bytes.fromhex(text))
''',
    "codec/url.py": '''"""URL form (application/x-www-form-urlencoded) percent-encoding."""

from urllib.parse import quote, unquote, unquote_plus


def url_encode(text: str) -> str:
    """Percent-encode ``text``, encoding spaces and reserved characters."""
    return quote(text, safe="")


def url_decode(text: str) -> str:
    """Decode percent-encoded form data, turning '+' into a space."""
    return unquote_plus(text)


def encode_query(params: dict) -> str:
    """Serialize ``params`` into a percent-encoded query string."""
    parts = []
    for key, value in params.items():
        parts.append(f"{quote(str(key), safe='')}={quote(str(value), safe='')}")
    return "&".join(parts)


def decode_query(query: str) -> dict:
    """Parse a percent-encoded query string into a dict of lists.

    A key may appear multiple times (``a=1&a=2`` -> ``{"a": ["1", "2"]}``) and a
    flag-only pair without ``=`` maps to an empty-string value.
    """
    result = {}
    for pair in query.split("&"):
        if not pair:
            continue
        if "=" in pair:
            key, value = pair.split("=", 1)
        else:
            key, value = pair, ""
        result.setdefault(unquote_plus(key), []).append(unquote_plus(value))
    return result
''',
    "codec/text.py": '''"""Text metrics and Unicode normalization."""

import unicodedata

from codec._bytes import to_bytes


def char_count(text: str) -> int:
    """Return the number of characters in ``text``."""
    return len(text)


def byte_count(text: str) -> int:
    """Return the number of UTF-8 bytes in ``text``."""
    return len(to_bytes(text))


def normalize(text: str) -> str:
    """Return the NFC-normalised form of ``text``."""
    return unicodedata.normalize("NFC", text)
''',
}

TESTS = {
    "tests/test_binary.py": '''from codec.binary import base64_decode, base64_encode, hex_decode, hex_encode


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
''',
    "tests/test_url.py": '''from codec.url import decode_query, encode_query, url_decode, url_encode


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
''',
    "tests/test_text.py": '''from codec.text import byte_count, char_count, normalize


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
    assert normalize("e\\u0301") == "\\u00e9"


def test_normalize_composed_two():
    assert normalize("a\\u0300") == "\\u00e0"


def test_normalize_already_nfc():
    assert normalize("hello") == "hello"
''',
    "tests/test_api.py": '''import codec


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
''',
}

TASKS = [
    {
        "id": "codec-01",
        "instruction": (
            "Fix `base64_encode` in `codec/binary.py` so it returns the ASCII text (a str), "
            "not the raw bytes object. The current code returns the `b64encode` result without "
            "decoding it to ASCII, so callers get `bytes` instead of a string."
        ),
        "difficulty": "easy",
        "category": "encoding",
        "lines": 1,
        "bug": [
            (
                "codec/binary.py",
                '    return base64.b64encode(to_bytes(data)).decode("ascii")',
                "    return base64.b64encode(to_bytes(data))",
            )
        ],
        "fail_to_pass": [
            "tests/test_binary.py::test_base64_encode_basic",
            "tests/test_binary.py::test_base64_encode_unicode",
        ],
        "pass_to_pass": [
            "tests/test_binary.py::test_base64_decode_basic",
            "tests/test_binary.py::test_hex_encode_basic",
            "tests/test_url.py::test_url_encode_spaces",
        ],
    },
    {
        "id": "codec-02",
        "instruction": (
            "Fix `base64_decode` in `codec/binary.py` so it returns the decoded UTF-8 string "
            "(a str), not the raw bytes object. It currently returns the `b64decode` result "
            "directly, leaking `bytes` to callers."
        ),
        "difficulty": "easy",
        "category": "encoding",
        "lines": 1,
        "bug": [
            (
                "codec/binary.py",
                "    return from_bytes(base64.b64decode(text))",
                "    return base64.b64decode(text)",
            )
        ],
        "fail_to_pass": [
            "tests/test_binary.py::test_base64_decode_basic",
            "tests/test_binary.py::test_base64_decode_unicode",
            "tests/test_binary.py::test_base64_encode_roundtrip",
        ],
        "pass_to_pass": [
            "tests/test_binary.py::test_base64_encode_basic",
            "tests/test_binary.py::test_hex_decode_basic",
            "tests/test_url.py::test_url_decode_percent",
        ],
    },
    {
        "id": "codec-03",
        "instruction": (
            "Fix `hex_encode` in `codec/binary.py` so it returns the hex string (a str), not the "
            "raw bytes. It currently returns the UTF-8 bytes directly instead of calling `.hex()` "
            "on them."
        ),
        "difficulty": "easy",
        "category": "encoding",
        "lines": 1,
        "bug": [
            (
                "codec/binary.py",
                "    return to_bytes(data).hex()",
                "    return to_bytes(data)",
            )
        ],
        "fail_to_pass": [
            "tests/test_binary.py::test_hex_encode_basic",
            "tests/test_binary.py::test_hex_roundtrip_unicode",
        ],
        "pass_to_pass": [
            "tests/test_binary.py::test_hex_decode_basic",
            "tests/test_binary.py::test_base64_encode_basic",
            "tests/test_text.py::test_char_count_ascii",
        ],
    },
    {
        "id": "codec-04",
        "instruction": (
            "Fix `encode_query` in `codec/url.py` so the *key* is percent-encoded the same way as "
            "the value. The current code interpolates the raw key into the query string without "
            "encoding it (and without `str()`-ing it), so keys containing spaces or reserved "
            "characters produce an invalid query string."
        ),
        "difficulty": "medium",
        "category": "url",
        "lines": 3,
        "bug": [
            (
                "codec/url.py",
                '        parts.append(f"{quote(str(key), safe=\'\')}={quote(str(value), safe=\'\')}")',
                '        parts.append(f"{key}={quote(str(value), safe=\'\')}")',
            )
        ],
        "fail_to_pass": [
            "tests/test_url.py::test_encode_query_encodes_key",
            "tests/test_url.py::test_encode_query_encodes_reserved",
        ],
        "pass_to_pass": [
            "tests/test_url.py::test_encode_query_basic",
            "tests/test_url.py::test_encode_query_encodes_value",
            "tests/test_url.py::test_url_encode_spaces",
            "tests/test_binary.py::test_base64_encode_basic",
        ],
    },
    {
        "id": "codec-05",
        "instruction": (
            "Fix `url_encode` in `codec/url.py` so reserved characters such as '/' are "
            "percent-encoded. It currently calls `quote` with the default `safe='/'`, which lets "
            "slashes pass through unencoded."
        ),
        "difficulty": "medium",
        "category": "url",
        "lines": 1,
        "bug": [
            (
                "codec/url.py",
                '    return quote(text, safe="")',
                "    return quote(text)",
            )
        ],
        "fail_to_pass": [
            "tests/test_url.py::test_url_encode_reserved",
            "tests/test_url.py::test_url_encode_multiple_slashes",
        ],
        "pass_to_pass": [
            "tests/test_url.py::test_url_encode_spaces",
            "tests/test_url.py::test_url_decode_percent",
            "tests/test_binary.py::test_base64_encode_basic",
        ],
    },
    {
        "id": "codec-06",
        "instruction": (
            "Fix `url_decode` in `codec/url.py` so a '+' is decoded as a space (form encoding). "
            "It currently uses `unquote`, which leaves '+' untouched instead of treating it as a "
            "space."
        ),
        "difficulty": "medium",
        "category": "url",
        "lines": 1,
        "bug": [
            (
                "codec/url.py",
                "    return unquote_plus(text)",
                "    return unquote(text)",
            )
        ],
        "fail_to_pass": [
            "tests/test_url.py::test_url_decode_plus",
            "tests/test_url.py::test_url_decode_plus_multiple",
        ],
        "pass_to_pass": [
            "tests/test_url.py::test_url_decode_percent",
            "tests/test_url.py::test_url_encode_spaces",
            "tests/test_binary.py::test_base64_decode_basic",
        ],
    },
    {
        "id": "codec-07",
        "instruction": (
            "Fix `byte_count` in `codec/text.py` so it counts UTF-8 bytes, not characters. "
            "Multi-byte characters (e.g. CJK) are currently under-counted because the code "
            "returns `len(text)` instead of the encoded byte length."
        ),
        "difficulty": "medium",
        "category": "text",
        "lines": 1,
        "bug": [
            (
                "codec/text.py",
                "    return len(to_bytes(text))",
                "    return len(text)",
            )
        ],
        "fail_to_pass": [
            "tests/test_text.py::test_byte_count_unicode",
            "tests/test_text.py::test_byte_count_unicode_two",
        ],
        "pass_to_pass": [
            "tests/test_text.py::test_byte_count_ascii",
            "tests/test_text.py::test_char_count_unicode",
            "tests/test_text.py::test_normalize_composed",
        ],
    },
    {
        "id": "codec-08",
        "instruction": (
            "Fix `normalize` in `codec/text.py` so it composes characters to NFC rather than "
            "decomposing to NFD. Precomposed input (e.g. a precomposed 'e-acute') is currently "
            "turned into a base letter plus a combining mark, which breaks NFC round-tripping."
        ),
        "difficulty": "hard",
        "category": "text",
        "lines": 1,
        "bug": [
            (
                "codec/text.py",
                '    return unicodedata.normalize("NFC", text)',
                '    return unicodedata.normalize("NFD", text)',
            )
        ],
        "fail_to_pass": [
            "tests/test_text.py::test_normalize_composed",
            "tests/test_text.py::test_normalize_composed_two",
        ],
        "pass_to_pass": [
            "tests/test_text.py::test_normalize_already_nfc",
            "tests/test_text.py::test_char_count_ascii",
            "tests/test_text.py::test_byte_count_ascii",
        ],
    },
    {
        "id": "codec-09",
        "instruction": (
            "Fix `to_bytes` in `codec/_bytes.py` so it encodes with UTF-8, not Latin-1. The "
            "Latin-1 codec cannot represent non-ASCII characters, so encoding or byte-counting "
            "any CJK text raises `UnicodeEncodeError` and breaks `base64_encode`, `hex_encode` "
            "and `byte_count`."
        ),
        "difficulty": "hard",
        "category": "encoding",
        "lines": 1,
        "bug": [
            (
                "codec/_bytes.py",
                '    return text.encode("utf-8")',
                '    return text.encode("latin-1")',
            )
        ],
        "fail_to_pass": [
            "tests/test_binary.py::test_base64_encode_unicode",
            "tests/test_binary.py::test_hex_roundtrip_unicode",
            "tests/test_text.py::test_byte_count_unicode",
            "tests/test_text.py::test_byte_count_unicode_two",
        ],
        "pass_to_pass": [
            "tests/test_binary.py::test_base64_encode_basic",
            "tests/test_binary.py::test_hex_encode_basic",
            "tests/test_text.py::test_char_count_ascii",
            "tests/test_text.py::test_byte_count_ascii",
            "tests/test_url.py::test_url_encode_spaces",
        ],
    },
    {
        "id": "codec-10",
        "instruction": (
            "Fix the package's public API in `codec/__init__.py` so `hex_encode` is exported. "
            "The `__init__` module currently forgets to import `hex_encode` from `codec.binary`, "
            "so `codec.hex_encode` is missing and callers get an `AttributeError`."
        ),
        "difficulty": "hard",
        "category": "api",
        "lines": 1,
        "bug": [
            (
                "codec/__init__.py",
                "from codec.binary import base64_decode, base64_encode, hex_decode, hex_encode",
                "from codec.binary import base64_decode, base64_encode, hex_decode",
            )
        ],
        "fail_to_pass": [
            "tests/test_api.py::test_api_all_public_names_present",
            "tests/test_api.py::test_api_hex_roundtrip",
        ],
        "pass_to_pass": [
            "tests/test_api.py::test_api_exports_base64",
            "tests/test_api.py::test_api_url_roundtrip",
            "tests/test_api.py::test_api_byte_count_unicode",
        ],
    },
    {
        "id": "codec-11",
        "instruction": (
            "Fix the package's public API in `codec/__init__.py` so `codec.byte_count` actually "
            "counts bytes. `__init__` currently aliases `byte_count` to `char_count`, so "
            "`codec.byte_count('中')` returns 1 instead of 3."
        ),
        "difficulty": "medium",
        "category": "api",
        "lines": 1,
        "bug": [
            (
                "codec/__init__.py",
                "from codec.text import byte_count, char_count, normalize",
                "from codec.text import char_count, char_count as byte_count, normalize",
            )
        ],
        "fail_to_pass": [
            "tests/test_api.py::test_api_byte_count_unicode",
        ],
        "pass_to_pass": [
            "tests/test_api.py::test_api_exports_base64",
            "tests/test_api.py::test_api_url_roundtrip",
            "tests/test_api.py::test_api_all_public_names_present",
            "tests/test_api.py::test_api_hex_roundtrip",
        ],
    },
    {
        "id": "codec-12",
        "instruction": (
            "Fix `decode_query` in `codec/url.py` so a flag-only pair (a key with no '=') is "
            "handled instead of crashing. The current code unconditionally unpacks `pair.split('=')`, "
            "so a bare flag like `?flag` raises `ValueError`; it should map to an empty-string value "
            "and still collect multiple values for the same key."
        ),
        "difficulty": "hard",
        "category": "url",
        "lines": 3,
        "bug": [
            (
                "codec/url.py",
                (
                    '        if "=" in pair:\n'
                    '            key, value = pair.split("=", 1)\n'
                    '        else:\n'
                    '            key, value = pair, ""\n'
                    "        result.setdefault(unquote_plus(key), []).append(unquote_plus(value))"
                ),
                (
                    '        key, value = pair.split("=", 1)\n'
                    "        result.setdefault(unquote_plus(key), []).append(unquote_plus(value))"
                ),
            )
        ],
        "fail_to_pass": [
            "tests/test_url.py::test_decode_query_flag",
            "tests/test_url.py::test_decode_query_flag_mixed",
        ],
        "pass_to_pass": [
            "tests/test_url.py::test_decode_query_basic",
            "tests/test_url.py::test_decode_query_multi_value",
            "tests/test_url.py::test_decode_query_plus",
        ],
    },
]
