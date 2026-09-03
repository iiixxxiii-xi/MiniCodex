"""URL form (application/x-www-form-urlencoded) percent-encoding."""

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
