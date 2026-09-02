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
            hi = mid
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
    out.extend(a[i:])
    out.extend(b[j:])
    return out


def remove_duplicates(seq):
    """Return ``seq`` with duplicates removed, preserving order."""
    return list(set(seq))


def rotate(seq, k):
    """Rotate ``seq`` to the left by ``k`` positions."""
    k = k % len(seq)
    return seq[k:] + seq[:k]


def partition(seq, pivot):
    """Return (left, right) where left <= pivot < right."""
    left = [x for x in seq if x <= pivot]
    right = [x for x in seq if x > pivot]
    return left, right


def flatten(nested):
    """Flatten a nested list of lists into a single list."""
    out = []
    for item in nested:
        if isinstance(item, list):
            out.extend(flatten(item))
        else:
            out.append(item)
    return out


def chunk(seq, size):
    """Split ``seq`` into chunks of ``size``."""
    return [seq[i:i + size] for i in range(0, len(seq), size)]


def max_subarray(nums):
    """Return the maximum subarray sum (Kadane's algorithm)."""
    best = nums[0]
    current = nums[0]
    for x in nums[1:]:
        current = max(x, current + x)
        best = max(best, current)
    return best
