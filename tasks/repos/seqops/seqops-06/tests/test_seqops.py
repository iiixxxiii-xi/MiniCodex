import seqops


def test_binary_search_first():
    assert seqops.binary_search([2, 3], 2) == 0


def test_binary_search_left():
    assert seqops.binary_search([1, 2, 3, 4], 2) == 1


def test_binary_search_middle():
    assert seqops.binary_search([1, 2, 3, 4, 5], 3) == 2


def test_binary_search_missing():
    assert seqops.binary_search([1, 2, 3], 4) == -1


def test_merge_sorted_one_exhausted():
    assert seqops.merge_sorted([1, 2], [3, 4]) == [1, 2, 3, 4]


def test_merge_sorted_interleaved():
    assert seqops.merge_sorted([1, 3], [2, 4]) == [1, 2, 3, 4]


def test_remove_duplicates_order():
    assert seqops.remove_duplicates([3, 1, 2, 1, 3]) == [3, 1, 2]


def test_remove_duplicates_order_two():
    assert seqops.remove_duplicates([5, 3, 5, 2, 3]) == [5, 3, 2]


def test_remove_duplicates_no_dupes():
    assert seqops.remove_duplicates([1, 2, 3]) == [1, 2, 3]


def test_rotate_wraparound():
    assert seqops.rotate([1, 2, 3], 5) == [3, 1, 2]


def test_rotate_wraparound_two():
    assert seqops.rotate([1, 2, 3], 4) == [2, 3, 1]


def test_rotate_full():
    assert seqops.rotate([1, 2, 3], 3) == [1, 2, 3]


def test_rotate_basic():
    assert seqops.rotate([1, 2, 3, 4, 5], 2) == [3, 4, 5, 1, 2]


def test_partition_equal_pivot():
    assert seqops.partition([1, 2, 2, 3], 2) == ([1, 2, 2], [3])


def test_partition_basic():
    assert seqops.partition([3, 1, 2, 4], 2) == ([1, 2], [3, 4])


def test_flatten_deep():
    assert seqops.flatten([[1, 2], [3, [4, 5]]]) == [1, 2, 3, 4, 5]


def test_flatten_deeper():
    assert seqops.flatten([[1, [2, [3]]]]) == [1, 2, 3]


def test_flatten_shallow():
    assert seqops.flatten([[1], [2, 3]]) == [1, 2, 3]


def test_chunk_partial():
    assert seqops.chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_chunk_exact():
    assert seqops.chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_max_subarray_all_negative():
    assert seqops.max_subarray([-2, -1, -3]) == -1


def test_max_subarray_single_negative():
    assert seqops.max_subarray([-5]) == -5


def test_max_subarray_positive():
    assert seqops.max_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6
