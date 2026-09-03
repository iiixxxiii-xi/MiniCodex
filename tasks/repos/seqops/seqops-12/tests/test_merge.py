from seqops.merge import merge_sorted


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
