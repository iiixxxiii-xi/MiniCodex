"""Sequence transforms: deduplicate, rotate, chunk, flatten, partition."""

from seqops._utils import default_compare


def remove_duplicates(items):
    """Return a new list of ``items`` with duplicates removed, order preserved."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def rotate(items, k):
    """Rotate ``items`` right by ``k`` positions.

    ``k`` may be negative (rotate left) or larger than ``len(items)``; it is
    reduced modulo the length first. An empty list is returned unchanged.
    """
    n = len(items)
    if n == 0:
        return []
    k %= n
    return items[-k:] + items[:-k]


def chunk(items, size):
    """Split ``items`` into consecutive chunks of ``size``.

    The final chunk is shorter when ``len(items)`` is not a multiple of
    ``size``. ``size`` must be a positive integer.
    """
    if size <= 0:
        raise ValueError("size must be a positive integer")
    return [items[i:i + size] for i in range(0, len(items), size)]


def flatten(nested):
    """Flatten arbitrarily nested lists into a single flat list (recursively)."""
    result = []
    for item in nested:
        if isinstance(item, list):
            result.extend(item)
        else:
            result.append(item)
    return result


def partition(items, pivot):
    """Partition ``items`` into ``(less, equal, greater)`` relative to ``pivot``.

    Each bucket preserves the original relative order of its elements.
    """
    less, equal, greater = [], [], []
    for item in items:
        c = default_compare(item, pivot)
        if c < 0:
            less.append(item)
        elif c == 0:
            equal.append(item)
        else:
            greater.append(item)
    return less, equal, greater
