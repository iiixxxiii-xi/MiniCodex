"""A small, dependency-free file-I/O helper library.

Public API:
- reading: ``read_lines`` / ``tail`` / ``count_lines``
- writing: ``safe_write`` / ``append_line``
- CSV: ``read_dicts`` / ``write_dicts``
- scanning: ``list_by_extension``
"""

from fileops.csvio import read_dicts, write_dicts
from fileops.read import count_lines, read_lines
from fileops.scan import list_by_extension
from fileops.write import append_line, safe_write

__all__ = [
    "read_lines",
    "tail",
    "count_lines",
    "safe_write",
    "append_line",
    "read_dicts",
    "write_dicts",
    "list_by_extension",
]
