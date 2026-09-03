"""Sequence-algorithms library: search, merge, transforms, and DP.

Public API:
- search: ``binary_search``
- merge: ``merge_sorted``
- transforms: ``remove_duplicates`` / ``rotate`` / ``chunk`` / ``flatten`` / ``partition``
- dynamic programming: ``max_subarray``
"""

from seqops.dynamic import max_subarray
from seqops.merge import merge_sorted
from seqops.search import binary_search
from seqops.transforms import chunk, flatten, partition, remove_duplicates, rotate

__all__ = [
    "binary_search",
    "merge_sorted",
    "remove_duplicates",
    "rotate",
    "chunk",
    "flatten",
    "partition",
    "max_subarray",
]
