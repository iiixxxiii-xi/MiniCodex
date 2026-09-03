"""Dynamic-programming sequence algorithms."""


def max_subarray(items):
    """Return the maximum sum of any contiguous subarray of ``items`` (Kadane's).

    Returns 0 for an empty sequence.
    """
    if not items:
        return 0
    best = cur = items[0]
    for x in items[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    return best
