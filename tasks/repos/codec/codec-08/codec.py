"""Small encoding/decoding utilities (intentionally buggy for eval tasks)."""

import base64
import unicodedata
from urllib.parse import quote, unquote, unquote_plus


def base64_encode(data):
    """Base64-encode a string and return the ASCII text."""
    return base64.b64encode(data.encode("utf-8")).decode("ascii")


def base64_decode(text):
    """Base64-decode ASCII text back into a UTF-8 string."""
    return base64.b64decode(text).decode("utf-8")


def hex_encode(data):
    """Hex-encode a string."""
    return data.encode("utf-8").hex()


def hex_decode(text):
    """Decode a hex string back into a UTF-8 string."""
    return bytes.fromhex(text).decode("utf-8")


def url_encode(text):
    """Percent-encode ``text`` (encoding spaces and reserved characters)."""
    return quote(text, safe="")


def url_decode(text):
    """Decode a percent-encoded (form) string, turning '+' into space."""
    return unquote_plus(text)


def char_count(text):
    """Return the number of characters in ``text``."""
    return len(text)


def byte_count(text):
    """Return the number of UTF-8 bytes in ``text``."""
    return len(text.encode("utf-8"))


def normalize(text):
    """Return the NFC-normalised form of ``text``."""
    return text
