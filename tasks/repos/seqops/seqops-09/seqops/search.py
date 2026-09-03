"""Search algorithms on sorted sequences."""


def binary_search(items, target):
    """Return the index of ``target`` in sorted ``items``, or -1 if not found.

    ``items`` must already be sorted in non-decreasing order. When ``target``
    occurs multiple times, the index of any occurrence is returned.
    """
    lo, hi = 0, len(items) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if items[mid] == target:
            return mid
        if items[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
