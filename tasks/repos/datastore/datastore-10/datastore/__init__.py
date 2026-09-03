"""A small JSON-backed document store with CSV I/O and a query layer.

Public API:
- ``DocumentStore`` — key -> document persistence with explicit close.
- ``parse_csv`` / ``parse_csv_dicts`` / ``to_csv`` — CSV import/export.
- ``filter_records`` / ``group_by`` / ``dedupe`` / ``aggregate`` — query helpers.
- ``dump_json`` / ``load_json`` — JSON serialization helpers.
"""

from datastore.csvio import parse_csv, parse_csv_dicts, to_csv
from datastore.jsonio import dump_json, load_json
from datastore.query import aggregate, dedupe, filter_records, group_by
from datastore.store import DocumentStore

__all__ = [
    "DocumentStore",
    "parse_csv",
    "parse_csv_dicts",
    "to_csv",
    "filter_records",
    "group_by",
    "dedupe",
    "aggregate",
    "dump_json",
    "load_json",
]
