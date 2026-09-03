import ds

from ds.ll import Node, append, from_seq, length, reverse, to_list


def test_length_empty():
    assert length(None) == 0


def test_length_single():
    assert length(Node(1)) == 1


def test_length_three():
    assert length(from_seq([1, 2, 3])) == 3


def test_append_to_empty():
    head = append(None, 1)
    assert to_list(head) == [1]


def test_append_to_existing():
    head = from_seq([1, 2, 3])
    head = append(head, 4)
    assert to_list(head) == [1, 2, 3, 4]


def test_append_single_element_list():
    head = from_seq([1])
    head = append(head, 2)
    assert to_list(head) == [1, 2]


def test_reverse_empty():
    assert reverse(None) is None


def test_reverse_single():
    assert to_list(reverse(from_seq([1]))) == [1]


def test_reverse_three():
    assert to_list(reverse(from_seq([1, 2, 3]))) == [3, 2, 1]


def test_reverse_four():
    assert to_list(reverse(from_seq([1, 2, 3, 4]))) == [4, 3, 2, 1]


def test_from_seq_order():
    assert to_list(from_seq([1, 2, 3])) == [1, 2, 3]


def test_to_list_empty():
    assert to_list(None) == []


def test_to_list_single():
    assert to_list(Node(7)) == [7]


def test_api_from_seq_to_list_roundtrip():
    head = ds.from_seq([1, 2, 3])
    assert ds.to_list(head) == [1, 2, 3]
