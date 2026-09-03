from seqops.search import binary_search


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
