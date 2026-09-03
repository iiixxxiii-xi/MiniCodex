"""A small text/config parsing library.

Public API:
- ``jsonio``: blank-tolerant JSON parsing (``load_json``)
- ``csvio``: CSV parsing honouring quoted fields (``parse_csv``)
- ``textutil``: line helpers + ``key=value`` parsing (``strip_comments``,
  ``split_words``, ``parse_kv``)
- ``ini``: INI-style config parsing (``parse_ini``)
"""

from parselib.csvio import parse_csv
from parselib.ini import parse_ini
from parselib.jsonio import load_json
from parselib.textutil import parse_kv, split_words, strip_comments

__all__ = [
    "parse_csv",
    "parse_ini",
    "load_json",
    "parse_kv",
    "split_words",
    "strip_comments",
]
