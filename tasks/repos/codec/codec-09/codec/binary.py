"""Binary text codecs: base64 and hexadecimal."""

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
