"""Small sequence-algorithm library (intentionally buggy for eval tasks)."""


def binary_search(arr, target):
    """Return the index of ``target`` in sorted ``arr``, or -1 if absent."""
    lo, hi = 0, len(arr)
    while lo < hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def merge_sorted(a, b):
    """Merge two sorted lists into one sorted list."""
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            out.append(a[i])
            i += 1
        else:
            out.append(b[j])
            j += 1
    return out


def remove_duplicates(seq):
    """Return ``seq`` with duplicates removed, preserving order."""
    return list(set(seq))


def rotate(seq, k):
    """Rotate ``seq`` to the left by ``k`` positions."""
    return seq[k:] + seq[:k]


def partition(seq, pivot):
    """Return (left, right) where left <= pivot < right."""
    left = [x for x in seq if x < pivot]
    right = [x for x in seq if x > pivot]
    return left, right


def flatten(nested):
    """Flatten a nested list of lists into a single list."""
    return [item for sublist in nested for item in sublist]


def chunk(seq, size):
    """Split ``seq`` into chunks of ``size``."""
    return [seq[i:i + size] for i in range(0, len(seq) - size, size)]


def max_subarray(nums):
    """Return the maximum subarray sum (Kadane's algorithm)."""
    best = 0
    current = 0
    for x in nums:
        current = max(x, current + x)
        best = max(best, current)
    return best
