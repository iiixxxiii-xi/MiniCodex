"""Shared str <-> bytes conversion helpers (private)."""


def to_bytes(text: str) -> bytes:
    """Encode ``text`` to its UTF-8 bytes."""
    return text.encode("utf-8")


def from_bytes(data: bytes) -> str:
    """Decode UTF-8 ``data`` back into a string."""
    return data.decode("utf-8")
