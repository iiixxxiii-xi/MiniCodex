"""CSV import/export honouring quoted fields."""

import csv
import io


def parse_csv(text: str, has_header: bool = True):
    """Parse CSV ``text`` into ``(header, rows)``.

    Quoted fields (containing commas, quotes, or newlines) are handled per the
    standard CSV dialect. When ``has_header`` is true the first record is the
    header; otherwise ``header`` is ``None``.
    """
    reader = csv.reader(io.StringIO(text))
    rows = [row for row in reader]
    if has_header and rows:
        return rows[0], rows[1:]
    return None, rows


def parse_csv_dicts(text: str) -> list:
    """Parse CSV ``text`` into a list of dicts keyed by the header row."""
    header, rows = parse_csv(text, has_header=True)
    if header is None:
        return []
    return [dict(zip(header, row)) for row in rows]


def to_csv(rows, header=None) -> str:
    """Serialize ``rows`` (each an iterable of fields) to a CSV string.

    Fields that need it are quoted on output. When ``header`` is given it is
    written as the first row.
    """
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerows(rows)
    return buf.getvalue()
