import seqops


def test_binary_search():
    assert seqops.binary_search([1, 2, 3, 4, 5], 3) == 2
    assert seqops.binary_search([2, 3], 2) == 0
    assert seqops.binary_search([1, 2, 3], 4) == -1


def test_merge_sorted():
    assert seqops.merge_sorted([1, 3], [2, 4]) == [1, 2, 3, 4]
    assert seqops.merge_sorted([1, 2], [3, 4]) == [1, 2, 3, 4]


def test_remove_duplicates():
    assert seqops.remove_duplicates([3, 1, 2, 1, 3]) == [3, 1, 2]


def test_rotate():
    assert seqops.rotate([1, 2, 3, 4, 5], 2) == [3, 4, 5, 1, 2]
    assert seqops.rotate([1, 2, 3], 3) == [1, 2, 3]
    assert seqops.rotate([1, 2, 3], 5) == [3, 1, 2]


def test_partition():
    assert seqops.partition([3, 1, 2, 4], 2) == ([1, 2], [3, 4])


def test_flatten():
    assert seqops.flatten([[1, 2], [3, [4, 5]]]) == [1, 2, 3, 4, 5]
    assert seqops.flatten([[1], [2, 3]]) == [1, 2, 3]


def test_chunk():
    assert seqops.chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_max_subarray():
    assert seqops.max_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6
    assert seqops.max_subarray([-2, -1, -3]) == -1
