from seqops.dynamic import max_subarray
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
