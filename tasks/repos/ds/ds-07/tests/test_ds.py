import pytest

import ds


def _ll(values):
    head = None
    tail = None
    for v in values:
        node = ds.Node(v)
        if head is None:
            head = node
        else:
            tail.next = node
        tail = node
    return head


def _values(head):
    out = []
    while head is not None:
        out.append(head.value)
        head = head.next
    return out


def test_linked_list_len_basic():
    assert ds.linked_list_len(_ll([1, 2, 3])) == 3


def test_linked_list_len_empty():
    assert ds.linked_list_len(None) == 0


def test_linked_list_append_build():
    assert _values(ds.linked_list_append(_ll([1, 2]), 3)) == [1, 2, 3]


def test_linked_list_append_single():
    assert _values(ds.linked_list_append(_ll([1]), 5)) == [1, 5]


def test_linked_list_append_empty():
    head = ds.linked_list_append(None, 5)
    assert head is not None and head.value == 5


def test_linked_list_reverse_basic():
    assert _values(ds.linked_list_reverse(_ll([1, 2, 3]))) == [3, 2, 1]


def test_linked_list_reverse_single():
    head = ds.linked_list_reverse(_ll([1]))
    assert head.value == 1 and head.next is None


def test_stack_push_pop():
    s = []
    ds.stack_push(s, 1)
    ds.stack_push(s, 2)
    assert ds.stack_pop(s) == 2
    assert ds.stack_pop(s) == 1


def test_stack_pop_empty_raises():
    with pytest.raises(IndexError):
        ds.stack_pop([])


def test_stack_pop_empty_message():
    with pytest.raises(IndexError, match="empty"):
        ds.stack_pop([])


def test_stack_peek_basic():
    assert ds.stack_peek([1, 2, 3]) == 3


def test_stack_peek_two():
    assert ds.stack_peek([5, 8]) == 8


def test_stack_peek_empty_raises():
    with pytest.raises(IndexError):
        ds.stack_peek([])


def test_ring_buffer_wraparound():
    rb = ds.RingBuffer(3)
    for v in [1, 2, 3, 4, 5]:
        rb.push(v)
    assert rb.to_list() == [3, 4, 5]


def test_ring_buffer_exact_full():
    rb = ds.RingBuffer(3)
    for v in [1, 2, 3, 4]:
        rb.push(v)
    assert rb.to_list() == [2, 3, 4]


def test_ring_buffer_partial():
    rb = ds.RingBuffer(3)
    rb.push(1)
    rb.push(2)
    assert rb.to_list() == [1, 2]


def test_lru_get_missing():
    assert ds.LRUCache(2).get("x") == -1


def test_lru_get_updates_recency():
    cache = ds.LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")
    cache.put("c", 3)
    assert cache.get("a") == 1
    assert cache.get("b") == -1


def test_lru_get_refreshes_after_eviction():
    cache = ds.LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("b")
    cache.put("d", 4)
    assert cache.get("b") == 2
    assert cache.get("c") == -1


def test_lru_put_evicts_least_recent():
    cache = ds.LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert cache.get("a") == -1
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_lru_put_capacity_one():
    cache = ds.LRUCache(1)
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == -1
    assert cache.get("b") == 2


def test_lru_put_updates_existing():
    cache = ds.LRUCache(2)
    cache.put("a", 1)
    cache.put("a", 99)
    assert cache.get("a") == 99


def test_binary_tree_height_basic():
    root = ds.TreeNode(1)
    root.left = ds.TreeNode(2)
    root.left.left = ds.TreeNode(3)
    assert ds.binary_tree_height(root) == 3


def test_binary_tree_height_single():
    root = ds.TreeNode(1)
    assert ds.binary_tree_height(root) == 1


def test_binary_tree_height_empty():
    assert ds.binary_tree_height(None) == 0
