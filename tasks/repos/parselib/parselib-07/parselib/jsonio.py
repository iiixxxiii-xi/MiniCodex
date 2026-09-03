"""Blank-tolerant JSON parsing built on the stdlib ``json`` module."""

import json

from parselib.textutil import strip_comments


def load_json(text: str):
    """Parse JSON ``text`` that may contain blank lines and ``#``/``;`` comments.

    Comments are stripped per line before parsing, and surrounding whitespace
    (including leading/trailing blank lines) is ignored.
    """
    cleaned = "\n".join(strip_comments(line) for line in text.splitlines())
    return json.loads(cleaned)
