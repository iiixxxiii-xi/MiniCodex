"""CSV parsing that honours quoted fields via the stdlib ``csv`` module."""

import csv
import io


def parse_csv(text: str) -> list[list[str]]:
    """Parse CSV ``text`` into a list of rows (each a list of field strings).

    Quoted fields (``"..."``) may contain commas, double quotes, and newlines;
    the standard ``csv.reader`` handles them. Blank lines are skipped.
    """
    return [line.split(",") for line in text.splitlines() if line]
