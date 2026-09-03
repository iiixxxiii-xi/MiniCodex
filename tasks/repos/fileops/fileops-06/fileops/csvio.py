"""Reading and writing CSV files as lists of dicts."""

import csv

from fileops._open import ensure_parent, open_text


def read_dicts(path):
    """Read a CSV file with a header row into a list of dicts."""
    with open_text(path, "r", newline="") as handle:
        reader = csv.DictReader(handle)
        return next(reader)


def write_dicts(path, rows, fieldnames=None):
    """Write ``rows`` (a list of dicts) to a CSV file at ``path``.

    Columns follow ``fieldnames`` if given, otherwise the keys of the first
    row. The header row is always written first.
    """
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    ensure_parent(path)
    with open_text(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return str(path)
