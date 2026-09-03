"""Repo spec: ``seqops`` — a multi-module sequence-algorithms library.

The library is a real multi-module package: a private ``_utils`` comparator
helper, four functional modules (``search`` / ``merge`` / ``transforms`` /
``dynamic``), and a public ``__init__`` that re-exports the API. Bugs span
modules (a broken shared ``default_compare`` in ``_utils`` breaks ``merge`` and
``transforms``) and range from one-line boundary slips to multi-line algorithmic
errors, plus two genuine cross-file integration bugs.
"""

REPO = "seqops"

FILES = {
    "seqops/__init__.py": '''"""Sequence-algorithms library: search, merge, transforms, and DP.

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
''',
    "seqops/_utils.py": '''"""Private shared helpers for the seqops package."""


def default_compare(a, b):
    """Three-way comparison of ``a`` and ``b``.

    Returns a negative int when ``a < b``, zero when equal, and a positive int
    when ``a > b`` (mirroring the legacy ``cmp`` builtin).
    """
    return (a > b) - (a < b)
''',
    "seqops/search.py": '''"""Search algorithms on sorted sequences."""


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
''',
    "seqops/merge.py": '''"""Merging sorted sequences."""

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
    result.extend(right[j:])
    return result
''',
    "seqops/transforms.py": '''"""Sequence transforms: deduplicate, rotate, chunk, flatten, partition."""

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
            result.extend(flatten(item))
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
''',
    "seqops/dynamic.py": '''"""Dynamic-programming sequence algorithms."""


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
''',
}

TESTS = {
    "tests/test_search.py": '''from seqops.search import binary_search


def test_found_first():
    assert binary_search([1, 2, 3, 4, 5], 1) == 0


def test_found_last():
    assert binary_search([1, 2, 3, 4, 5], 5) == 4


def test_found_middle():
    assert binary_search([1, 2, 3, 4, 5], 3) == 2


def test_missing_below():
    assert binary_search([1, 2, 3, 4, 5], 0) == -1


def test_missing_above():
    assert binary_search([1, 2, 3, 4, 5], 6) == -1


def test_missing_middle():
    assert binary_search([1, 3, 5, 7], 4) == -1


def test_single_found():
    assert binary_search([42], 42) == 0


def test_single_missing():
    assert binary_search([42], 7) == -1


def test_empty():
    assert binary_search([], 1) == -1
''',
    "tests/test_merge.py": '''from seqops.merge import merge_sorted


def test_basic():
    assert merge_sorted([1, 3, 5], [2, 4, 6]) == [1, 2, 3, 4, 5, 6]


def test_left_exhausted():
    assert merge_sorted([1, 2], [3, 4, 5]) == [1, 2, 3, 4, 5]


def test_right_exhausted():
    assert merge_sorted([3, 4, 5], [1, 2]) == [1, 2, 3, 4, 5]


def test_equal_elements():
    assert merge_sorted([1, 2, 2], [2, 3]) == [1, 2, 2, 2, 3]


def test_one_empty():
    assert merge_sorted([1, 2, 3], []) == [1, 2, 3]


def test_both_empty():
    assert merge_sorted([], []) == []
''',
    "tests/test_transforms.py": '''from seqops.dynamic import max_subarray
from seqops.transforms import chunk, flatten, partition, remove_duplicates, rotate


def test_remove_duplicates_basic():
    assert remove_duplicates([1, 2, 2, 3, 3, 3]) == [1, 2, 3]


def test_remove_duplicates_order():
    assert remove_duplicates([3, 1, 3, 2, 1]) == [3, 1, 2]


def test_remove_duplicates_nonadjacent():
    assert remove_duplicates([1, 2, 1, 2, 1]) == [1, 2]


def test_remove_duplicates_empty():
    assert remove_duplicates([]) == []


def test_rotate_right():
    assert rotate([1, 2, 3, 4, 5], 2) == [4, 5, 1, 2, 3]


def test_rotate_k_gt_len():
    assert rotate([1, 2, 3, 4, 5], 7) == [4, 5, 1, 2, 3]


def test_rotate_k_much_gt_len():
    assert rotate([1, 2, 3, 4, 5], 12) == [4, 5, 1, 2, 3]


def test_rotate_negative():
    assert rotate([1, 2, 3, 4, 5], -1) == [2, 3, 4, 5, 1]


def test_rotate_negative_multiple():
    assert rotate([1, 2, 3, 4, 5], -3) == [4, 5, 1, 2, 3]


def test_rotate_zero():
    assert rotate([1, 2, 3, 4, 5], 0) == [1, 2, 3, 4, 5]


def test_chunk_even():
    assert chunk([1, 2, 3, 4, 5, 6], 2) == [[1, 2], [3, 4], [5, 6]]


def test_chunk_partial():
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_chunk_larger():
    assert chunk([1, 2, 3], 5) == [[1, 2, 3]]


def test_chunk_size_one():
    assert chunk([1, 2, 3], 1) == [[1], [2], [3]]


def test_flatten_deep():
    assert flatten([1, [2, [3, [4, [5]]]]]) == [1, 2, 3, 4, 5]


def test_flatten_very_deep():
    assert flatten([[[[1]]]]) == [1]


def test_flatten_one_level():
    assert flatten([1, [2, 3], 4]) == [1, 2, 3, 4]


def test_flatten_flat():
    assert flatten([1, 2, 3]) == [1, 2, 3]


def test_flatten_empty():
    assert flatten([]) == []


def test_partition_basic():
    assert partition([3, 1, 4, 1, 5, 9, 2, 6], 4) == ([3, 1, 1, 2], [4], [5, 9, 6])


def test_partition_pivot_equal():
    assert partition([5, 1, 5, 2, 5, 3], 5) == ([1, 2, 3], [5, 5, 5], [])


def test_partition_no_equal():
    assert partition([1, 2, 3], 10) == ([1, 2, 3], [], [])


def test_max_subarray_basic():
    assert max_subarray([1, -3, 2, 1, -1]) == 3


def test_max_subarray_all_negative():
    assert max_subarray([-2, -3, -1, -5]) == -1


def test_max_subarray_single():
    assert max_subarray([-5]) == -5


def test_max_subarray_empty():
    assert max_subarray([]) == 0


def test_max_subarray_positive():
    assert max_subarray([1, 2, 3, 4]) == 10
''',
}

TASKS = [
    {
        "id": "seqops-01",
        "instruction": (
            "Fix `binary_search` in `seqops/search.py` so it finds the last element of a "
            "sorted list and the only element of a single-element list. It currently exits its "
            "loop one iteration too early, so searching for the last element (or the sole element "
            "of a one-element list) returns -1 instead of the correct index."
        ),
        "difficulty": "easy",
        "category": "search",
        "lines": 1,
        "bug": [
            ("seqops/search.py", "    while lo <= hi:", "    while lo < hi:"),
        ],
        "fail_to_pass": [
            "tests/test_search.py::test_found_last",
            "tests/test_search.py::test_single_found",
        ],
        "pass_to_pass": [
            "tests/test_search.py::test_found_first",
            "tests/test_search.py::test_found_middle",
            "tests/test_search.py::test_missing_below",
            "tests/test_search.py::test_missing_above",
            "tests/test_search.py::test_empty",
        ],
    },
    {
        "id": "seqops-02",
        "instruction": (
            "Fix `binary_search` in `seqops/search.py` so it returns -1 when the target is not "
            "present in the sorted list. It currently returns the loop variable as if it were an "
            "insertion index, so every missing target yields a non-negative index instead of -1."
        ),
        "difficulty": "easy",
        "category": "search",
        "lines": 1,
        "bug": [
            ("seqops/search.py", "    return -1", "    return lo"),
        ],
        "fail_to_pass": [
            "tests/test_search.py::test_missing_below",
            "tests/test_search.py::test_missing_above",
            "tests/test_search.py::test_missing_middle",
        ],
        "pass_to_pass": [
            "tests/test_search.py::test_found_first",
            "tests/test_search.py::test_found_last",
            "tests/test_search.py::test_found_middle",
            "tests/test_search.py::test_single_found",
        ],
    },
    {
        "id": "seqops-03",
        "instruction": (
            "Fix `merge_sorted` in `seqops/merge.py` so it keeps the remaining elements of the "
            "right list once the left list is exhausted. It currently drops the right tail, so "
            "merging [1, 2] with [3, 4, 5] loses 3, 4 and 5."
        ),
        "difficulty": "medium",
        "category": "merge",
        "lines": 1,
        "bug": [
            (
                "seqops/merge.py",
                "    result.extend(left[i:])\n    result.extend(right[j:])",
                "    result.extend(left[i:])",
            ),
        ],
        "fail_to_pass": [
            "tests/test_merge.py::test_left_exhausted",
            "tests/test_merge.py::test_basic",
        ],
        "pass_to_pass": [
            "tests/test_merge.py::test_right_exhausted",
            "tests/test_merge.py::test_one_empty",
            "tests/test_merge.py::test_both_empty",
        ],
    },
    {
        "id": "seqops-04",
        "instruction": (
            "Fix `remove_duplicates` in `seqops/transforms.py` so it removes every duplicate "
            "occurrence, not just consecutive ones, while preserving first-occurrence order. "
            "Non-adjacent duplicates currently survive in the output."
        ),
        "difficulty": "easy",
        "category": "transforms",
        "lines": 6,
        "bug": [
            (
                "seqops/transforms.py",
                (
                    "    seen = set()\n"
                    "    result = []\n"
                    "    for item in items:\n"
                    "        if item not in seen:\n"
                    "            seen.add(item)\n"
                    "            result.append(item)\n"
                    "    return result"
                ),
                (
                    "    result = []\n"
                    "    for item in items:\n"
                    "        if not result or result[-1] != item:\n"
                    "            result.append(item)\n"
                    "    return result"
                ),
            ),
        ],
        "fail_to_pass": [
            "tests/test_transforms.py::test_remove_duplicates_order",
            "tests/test_transforms.py::test_remove_duplicates_nonadjacent",
        ],
        "pass_to_pass": [
            "tests/test_transforms.py::test_remove_duplicates_basic",
            "tests/test_transforms.py::test_remove_duplicates_empty",
        ],
    },
    {
        "id": "seqops-05",
        "instruction": (
            "Fix `rotate` in `seqops/transforms.py` so a rotation count larger than the list "
            "length is handled correctly. It currently uses `k` directly without reducing it "
            "modulo the length, so `rotate(items, k)` with `k > len(items)` returns the "
            "unrotated list."
        ),
        "difficulty": "medium",
        "category": "transforms",
        "lines": 1,
        "bug": [
            (
                "seqops/transforms.py",
                "    k %= n\n    return items[-k:] + items[:-k]",
                "    return items[-k:] + items[:-k]",
            ),
        ],
        "fail_to_pass": [
            "tests/test_transforms.py::test_rotate_k_gt_len",
            "tests/test_transforms.py::test_rotate_k_much_gt_len",
        ],
        "pass_to_pass": [
            "tests/test_transforms.py::test_rotate_right",
            "tests/test_transforms.py::test_rotate_negative",
            "tests/test_transforms.py::test_rotate_negative_multiple",
            "tests/test_transforms.py::test_rotate_zero",
        ],
    },
    {
        "id": "seqops-06",
        "instruction": (
            "Fix `rotate` in `seqops/transforms.py` so negative rotation counts rotate to the "
            "left. It currently takes the absolute value of `k`, so `rotate(items, -1)` rotates "
            "right by one instead of left by one."
        ),
        "difficulty": "medium",
        "category": "transforms",
        "lines": 1,
        "bug": [
            (
                "seqops/transforms.py",
                "    k %= n\n    return items[-k:] + items[:-k]",
                "    k = abs(k) % n\n    return items[-k:] + items[:-k]",
            ),
        ],
        "fail_to_pass": [
            "tests/test_transforms.py::test_rotate_negative",
            "tests/test_transforms.py::test_rotate_negative_multiple",
        ],
        "pass_to_pass": [
            "tests/test_transforms.py::test_rotate_right",
            "tests/test_transforms.py::test_rotate_k_gt_len",
            "tests/test_transforms.py::test_rotate_k_much_gt_len",
            "tests/test_transforms.py::test_rotate_zero",
        ],
    },
    {
        "id": "seqops-07",
        "instruction": (
            "Fix `chunk` in `seqops/transforms.py` so the final partial chunk is included in the "
            "result. It currently only emits full-size chunks, dropping the trailing remainder "
            "when `len(items)` is not a multiple of `size`."
        ),
        "difficulty": "easy",
        "category": "transforms",
        "lines": 1,
        "bug": [
            (
                "seqops/transforms.py",
                "    return [items[i:i + size] for i in range(0, len(items), size)]",
                "    return [items[i:i + size] for i in range(0, len(items) - size + 1, size)]",
            ),
        ],
        "fail_to_pass": [
            "tests/test_transforms.py::test_chunk_partial",
            "tests/test_transforms.py::test_chunk_larger",
        ],
        "pass_to_pass": [
            "tests/test_transforms.py::test_chunk_even",
            "tests/test_transforms.py::test_chunk_size_one",
        ],
    },
    {
        "id": "seqops-08",
        "instruction": (
            "Fix `flatten` in `seqops/transforms.py` so it flattens arbitrarily deeply nested "
            "lists. It currently flattens only one level, so nested sublists survive in the "
            "output instead of being recursively unwrapped."
        ),
        "difficulty": "medium",
        "category": "transforms",
        "lines": 1,
        "bug": [
            (
                "seqops/transforms.py",
                (
                    "    for item in nested:\n"
                    "        if isinstance(item, list):\n"
                    "            result.extend(flatten(item))\n"
                    "        else:\n"
                    "            result.append(item)"
                ),
                (
                    "    for item in nested:\n"
                    "        if isinstance(item, list):\n"
                    "            result.extend(item)\n"
                    "        else:\n"
                    "            result.append(item)"
                ),
            ),
        ],
        "fail_to_pass": [
            "tests/test_transforms.py::test_flatten_deep",
            "tests/test_transforms.py::test_flatten_very_deep",
        ],
        "pass_to_pass": [
            "tests/test_transforms.py::test_flatten_one_level",
            "tests/test_transforms.py::test_flatten_flat",
            "tests/test_transforms.py::test_flatten_empty",
        ],
    },
    {
        "id": "seqops-09",
        "instruction": (
            "Fix `partition` in `seqops/transforms.py` so elements equal to the pivot land in the "
            "`equal` bucket. It currently lacks an equal branch, so pivot-equal elements are "
            "misclassified into the `greater` bucket."
        ),
        "difficulty": "medium",
        "category": "transforms",
        "lines": 2,
        "bug": [
            (
                "seqops/transforms.py",
                (
                    "        c = default_compare(item, pivot)\n"
                    "        if c < 0:\n"
                    "            less.append(item)\n"
                    "        elif c == 0:\n"
                    "            equal.append(item)\n"
                    "        else:\n"
                    "            greater.append(item)"
                ),
                (
                    "        c = default_compare(item, pivot)\n"
                    "        if c < 0:\n"
                    "            less.append(item)\n"
                    "        else:\n"
                    "            greater.append(item)"
                ),
            ),
        ],
        "fail_to_pass": [
            "tests/test_transforms.py::test_partition_pivot_equal",
            "tests/test_transforms.py::test_partition_basic",
        ],
        "pass_to_pass": [
            "tests/test_transforms.py::test_partition_no_equal",
        ],
    },
    {
        "id": "seqops-10",
        "instruction": (
            "Fix `max_subarray` in `seqops/dynamic.py` so it returns the correct maximum for lists "
            "of all-negative numbers (the largest single element) and single-element lists. It "
            "currently initialises the running best to 0, which over-counts when every element is "
            "negative."
        ),
        "difficulty": "hard",
        "category": "dynamic-programming",
        "lines": 2,
        "bug": [
            (
                "seqops/dynamic.py",
                "    best = cur = items[0]\n    for x in items[1:]:",
                "    best = cur = 0\n    for x in items:",
            ),
        ],
        "fail_to_pass": [
            "tests/test_transforms.py::test_max_subarray_all_negative",
            "tests/test_transforms.py::test_max_subarray_single",
        ],
        "pass_to_pass": [
            "tests/test_transforms.py::test_max_subarray_basic",
            "tests/test_transforms.py::test_max_subarray_positive",
            "tests/test_transforms.py::test_max_subarray_empty",
        ],
    },
    {
        "id": "seqops-11",
        "instruction": (
            "Fix `partition` in `seqops/transforms.py` (and the shared comparator it relies on) so "
            "elements equal to the pivot land in the `equal` bucket. A refactor changed "
            "`default_compare` in `seqops/_utils.py` to return a boolean and rewrote `partition` "
            "without an equal branch, so pivot-equal elements are misclassified into `greater`."
        ),
        "difficulty": "hard",
        "category": "integration",
        "lines": 4,
        "bug": [
            ("seqops/_utils.py", "    return (a > b) - (a < b)", "    return a < b"),
            (
                "seqops/merge.py",
                "        if default_compare(left[i], right[j]) <= 0:",
                "        if default_compare(left[i], right[j]):",
            ),
            (
                "seqops/transforms.py",
                (
                    "        c = default_compare(item, pivot)\n"
                    "        if c < 0:\n"
                    "            less.append(item)\n"
                    "        elif c == 0:\n"
                    "            equal.append(item)\n"
                    "        else:\n"
                    "            greater.append(item)"
                ),
                (
                    "        if default_compare(item, pivot):\n"
                    "            less.append(item)\n"
                    "        else:\n"
                    "            greater.append(item)"
                ),
            ),
        ],
        "fail_to_pass": [
            "tests/test_transforms.py::test_partition_pivot_equal",
            "tests/test_transforms.py::test_partition_basic",
        ],
        "pass_to_pass": [
            "tests/test_transforms.py::test_partition_no_equal",
            "tests/test_merge.py::test_basic",
            "tests/test_merge.py::test_left_exhausted",
            "tests/test_merge.py::test_right_exhausted",
            "tests/test_search.py::test_found_first",
        ],
    },
    {
        "id": "seqops-12",
        "instruction": (
            "Fix `merge_sorted` in `seqops/merge.py` (and the shared comparator it relies on) so it "
            "produces ascending output and keeps the right list's remaining elements. The shared "
            "comparator `default_compare` in `seqops/_utils.py` is inverted and the tail-extend for "
            "the right list was dropped, so merges come out descending and truncated."
        ),
        "difficulty": "hard",
        "category": "integration",
        "lines": 2,
        "bug": [
            ("seqops/_utils.py", "    return (a > b) - (a < b)", "    return (a < b) - (a > b)"),
            (
                "seqops/merge.py",
                "    result.extend(left[i:])\n    result.extend(right[j:])",
                "    result.extend(left[i:])",
            ),
        ],
        "fail_to_pass": [
            "tests/test_merge.py::test_basic",
            "tests/test_merge.py::test_left_exhausted",
            "tests/test_merge.py::test_right_exhausted",
        ],
        "pass_to_pass": [
            "tests/test_merge.py::test_one_empty",
            "tests/test_merge.py::test_both_empty",
            "tests/test_search.py::test_found_first",
            "tests/test_search.py::test_found_last",
        ],
    },
]
