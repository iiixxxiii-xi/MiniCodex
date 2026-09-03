"""A small, dependency-free encoding/decoding library.

Public API:
- binary codecs: ``base64_encode`` / ``base64_decode``, ``hex_encode`` / ``hex_decode``
- URL form codecs: ``url_encode`` / ``url_decode`` / ``encode_query``
- text metrics + normalization: ``char_count`` / ``byte_count`` / ``normalize``
"""

from codec.binary import base64_decode, base64_encode, hex_decode
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
