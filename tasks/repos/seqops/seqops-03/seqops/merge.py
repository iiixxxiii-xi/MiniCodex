"""Merging sorted sequences."""

from seqops._utils import default_compare


def merge_sorted(left, right):
    """Merge two sorted lists into one sorted list (stable, non-decreasing)."""
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if default_compare(left[i], right[j]) <= 0:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    return result
