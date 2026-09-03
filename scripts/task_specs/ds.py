"""Repo spec: ``ds`` — a small, multi-module data-structure library.

This spec turns ``ds`` from a toy single-module into a real mini library:
separate modules for a linked list (``ll``), a linked-list-backed stack
(``stack``), a ring buffer (``ring``), an LRU cache (``lru``), a binary tree
(``tree``), and a thread-safe counter (``counter``). Modules share real
cross-module imports: ``stack`` uses ``ll.Node``, ``lru`` uses ``counter.Counter``,
and ``__init__`` re-exports the public API. Bugs range from one-line off-by-one /
boundary slips to multi-line algorithmic errors, a genuine concurrency bug
(non-atomic counter increment), and cross-file integration bugs that span two
modules.
"""

REPO = "ds"

FILES = {
    "ds/__init__.py": '''"""A small, dependency-free data-structure library.

Public API:
- linked list: ``Node``, ``from_seq``, ``length``, ``append``, ``reverse``, ``to_list``
- ``Stack``
- ``RingBuffer``
- ``LRUCache``
- ``TreeNode``, ``height``
- ``Counter``
"""

from ds.counter import Counter
from ds.ll import Node, append, from_seq, length, reverse, to_list
from ds.lru import LRUCache
from ds.ring import RingBuffer
from ds.stack import Stack
from ds.tree import TreeNode, height

__all__ = [
    "Node",
    "from_seq",
    "length",
    "append",
    "reverse",
    "to_list",
    "Stack",
    "RingBuffer",
    "LRUCache",
    "TreeNode",
    "height",
    "Counter",
]
''',
    "ds/ll.py": '''"""A singly linked list.

The list is represented by a head :class:`Node`; the empty list is ``None``.
"""


class Node:
    """A single node holding a value and a link to the next node."""

    def __init__(self, value, nxt=None):
        self.value = value
        self.nxt = nxt


def from_seq(seq):
    """Build a linked list from an iterable, returning the head node."""
    head = None
    for item in reversed(seq):
        head = Node(item, head)
    return head


def length(head):
    """Return the number of nodes in the list rooted at ``head``."""
    n = 0
    cur = head
    while cur is not None:
        n += 1
        cur = cur.nxt
    return n


def append(head, value):
    """Append ``value`` to the end of the list, returning the (possibly new) head."""
    if head is None:
        return Node(value)
    cur = head
    while cur.nxt is not None:
        cur = cur.nxt
    cur.nxt = Node(value)
    return head


def reverse(head):
    """Reverse the list in place and return the new head."""
    prev = None
    cur = head
    while cur is not None:
        nxt = cur.nxt
        cur.nxt = prev
        prev = cur
        cur = nxt
    return prev


def to_list(head):
    """Convert a linked list back into a Python list."""
    out = []
    cur = head
    while cur is not None:
        out.append(cur.value)
        cur = cur.nxt
    return out
''',
    "ds/stack.py": '''"""A last-in-first-out stack backed by a singly linked list."""

from ds.ll import Node


class Stack:
    """A simple stack supporting push/pop/peek and len()."""

    def __init__(self):
        self._head = None

    def push(self, item):
        self._head = Node(item, self._head)

    def pop(self):
        if self._head is None:
            raise IndexError("pop from empty stack")
        item = self._head.value
        self._head = self._head.nxt
        return item

    def peek(self):
        if self._head is None:
            raise IndexError("peek from empty stack")
        return self._head.value

    def is_empty(self):
        return self._head is None

    def __len__(self):
        n = 0
        cur = self._head
        while cur is not None:
            n += 1
            cur = cur.nxt
        return n
''',
    "ds/ring.py": '''"""A fixed-capacity ring buffer (FIFO)."""


class RingBuffer:
    """A circular buffer that rejects writes when full."""

    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._buf = [None] * capacity
        self._size = 0
        self._head = 0

    def __len__(self):
        return self._size

    @property
    def capacity(self):
        return self._capacity

    def is_full(self):
        return self._size == self._capacity

    def is_empty(self):
        return self._size == 0

    def push(self, item):
        if self.is_full():
            raise OverflowError("ring buffer is full")
        tail = (self._head + self._size) % self._capacity
        self._buf[tail] = item
        self._size += 1

    def pop(self):
        if self.is_empty():
            raise IndexError("pop from empty ring buffer")
        item = self._buf[self._head]
        self._buf[self._head] = None
        self._head = (self._head + 1) % self._capacity
        self._size -= 1
        return item

    def peek(self):
        if self.is_empty():
            raise IndexError("peek from empty ring buffer")
        return self._buf[self._head]

    def to_list(self):
        out = []
        for i in range(self._size):
            out.append(self._buf[(self._head + i) % self._capacity])
        return out
''',
    "ds/lru.py": '''"""A least-recently-used cache backed by an ordered dict."""

from collections import OrderedDict

from ds.counter import Counter


class LRUCache:
    """A fixed-capacity cache that evicts the least-recently-used entry."""

    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._cache = OrderedDict()
        self.hits = Counter()
        self.misses = Counter()

    def get(self, key):
        if key not in self._cache:
            self.misses.increment()
            return -1
        value = self._cache.pop(key)
        self._cache[key] = value
        self.hits.increment()
        return value

    def put(self, key, value):
        if key in self._cache:
            self._cache.pop(key)
        elif len(self._cache) >= self.capacity:
            self._cache.popitem(last=False)
        self._cache[key] = value

    def __len__(self):
        return len(self._cache)

    def __contains__(self, key):
        return key in self._cache
''',
    "ds/tree.py": '''"""Binary tree helpers."""


class TreeNode:
    """A binary tree node."""

    def __init__(self, value, left=None, right=None):
        self.value = value
        self.left = left
        self.right = right


def height(node):
    """Return the height of the tree rooted at ``node``.

    The height is the number of nodes on the longest path from the root down
    to a leaf: an empty tree has height 0 and a single node has height 1.
    """
    if node is None:
        return 0
    return 1 + max(height(node.left), height(node.right))
''',
    "ds/counter.py": '''"""A thread-safe integer counter."""

import threading
import time


class Counter:
    """An integer counter safe to use from multiple threads."""

    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()

    def increment(self, n=1):
        """Add ``n`` to the counter and return the new value."""
        with self._lock:
            self._value += n
        return self._value

    @property
    def value(self):
        with self._lock:
            return self._value

    def reset(self):
        with self._lock:
            self._value = 0
''',
}

TESTS = {
    "tests/test_ll.py": '''import ds

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
''',
    "tests/test_stack_ring.py": '''import pytest

from ds.ring import RingBuffer
from ds.stack import Stack


def test_stack_push_pop():
    s = Stack()
    s.push(1)
    s.push(2)
    assert s.pop() == 2
    assert s.pop() == 1


def test_stack_pop_empty_raises():
    s = Stack()
    with pytest.raises(IndexError):
        s.pop()


def test_stack_peek():
    s = Stack()
    s.push(10)
    s.push(20)
    assert s.peek() == 20


def test_stack_peek_empty_raises():
    s = Stack()
    with pytest.raises(IndexError):
        s.peek()


def test_stack_is_empty():
    s = Stack()
    assert s.is_empty()
    s.push(1)
    assert not s.is_empty()


def test_stack_len():
    s = Stack()
    assert len(s) == 0
    s.push(1)
    s.push(2)
    s.push(3)
    assert len(s) == 3


def test_stack_len_after_pop():
    s = Stack()
    s.push(1)
    s.push(2)
    s.pop()
    assert len(s) == 1


def test_ring_push_pop():
    r = RingBuffer(3)
    r.push(1)
    r.push(2)
    r.push(3)
    assert r.pop() == 1
    assert r.pop() == 2
    assert r.pop() == 3


def test_ring_full():
    r = RingBuffer(2)
    r.push(1)
    r.push(2)
    assert r.is_full()


def test_ring_push_full_raises():
    r = RingBuffer(1)
    r.push(1)
    with pytest.raises(OverflowError):
        r.push(2)


def test_ring_wraparound():
    r = RingBuffer(3)
    r.push(1)
    r.push(2)
    r.push(3)
    assert r.pop() == 1
    r.push(4)
    assert r.to_list() == [2, 3, 4]


def test_ring_wraparound_order():
    r = RingBuffer(2)
    r.push(1)
    r.push(2)
    r.pop()
    r.push(3)
    assert r.to_list() == [2, 3]


def test_ring_pop_empty_raises():
    r = RingBuffer(2)
    with pytest.raises(IndexError):
        r.pop()


def test_ring_peek():
    r = RingBuffer(2)
    r.push(5)
    r.push(6)
    assert r.peek() == 5


def test_ring_len():
    r = RingBuffer(3)
    assert len(r) == 0
    r.push(1)
    r.push(2)
    assert len(r) == 2
''',
    "tests/test_lru_tree.py": '''import threading

from ds.counter import Counter
from ds.lru import LRUCache
from ds.tree import TreeNode, height


def test_lru_get_missing():
    c = LRUCache(2)
    assert c.get("a") == -1


def test_lru_put_get():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1
    assert c.get("b") == 2


def test_lru_evicts_oldest():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    assert c.get("a") == -1
    assert c.get("b") == 2
    assert c.get("c") == 3


def test_lru_evicts_least_recently_used():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")
    c.put("c", 3)
    assert c.get("b") == -1
    assert c.get("a") == 1
    assert c.get("c") == 3


def test_lru_capacity_one():
    c = LRUCache(1)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == -1
    assert c.get("b") == 2


def test_lru_update_existing():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("a", 100)
    assert c.get("a") == 100
    assert len(c) == 1


def test_lru_len_and_contains():
    c = LRUCache(2)
    c.put("a", 1)
    assert len(c) == 1
    assert "a" in c
    assert "b" not in c


def test_lru_hit_miss_counts():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")
    c.get("b")
    c.get("c")
    assert c.hits.value == 2
    assert c.misses.value == 1


def test_counter_increment():
    c = Counter()
    assert c.increment() == 1
    assert c.increment() == 2
    assert c.value == 2


def test_counter_increment_by_n():
    c = Counter()
    c.increment(5)
    assert c.value == 5


def test_counter_reset():
    c = Counter()
    c.increment(10)
    c.reset()
    assert c.value == 0


def test_counter_concurrent_increment():
    c = Counter()
    n_threads = 8
    n_increments = 1000
    barrier = threading.Barrier(n_threads)

    def worker():
        barrier.wait()
        for _ in range(n_increments):
            c.increment()

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert c.value == n_threads * n_increments


def test_tree_height_empty():
    assert height(None) == 0


def test_tree_height_single():
    assert height(TreeNode(1)) == 1


def test_tree_height_balanced():
    root = TreeNode(1, TreeNode(2), TreeNode(3))
    assert height(root) == 2


def test_tree_height_unbalanced():
    root = TreeNode(1, TreeNode(2, TreeNode(3, TreeNode(4))))
    assert height(root) == 4


def test_tree_height_skewed_right():
    root = TreeNode(1, right=TreeNode(2, right=TreeNode(3)))
    assert height(root) == 3
''',
}

TASKS = [
    {
        "id": "ds-01",
        "instruction": (
            "`ds.length` (in `ds/ll.py`) returns one element too few for a non-empty "
            "list. A single-node list is reported as length 0 and a three-node list as "
            "length 2, because the traversal stops one node before the end. The empty "
            "list is reported correctly."
        ),
        "difficulty": "easy",
        "category": "linked-list",
        "lines": 1,
        "bug": [
            (
                "ds/ll.py",
                "    while cur is not None:\n        n += 1\n        cur = cur.nxt\n    return n",
                "    while cur is not None and cur.nxt is not None:\n        n += 1\n        cur = cur.nxt\n    return n",
            )
        ],
        "fail_to_pass": [
            "tests/test_ll.py::test_length_single",
            "tests/test_ll.py::test_length_three",
        ],
        "pass_to_pass": [
            "tests/test_ll.py::test_length_empty",
            "tests/test_ll.py::test_from_seq_order",
            "tests/test_ll.py::test_to_list_single",
        ],
    },
    {
        "id": "ds-02",
        "instruction": (
            "`ds/ll.py::to_list` drops the last node when converting a linked list back "
            "to a Python list. A single-node list comes back as `[]` and a three-node "
            "list as a two-element list, because the loop stops before visiting the final "
            "node; the empty list also raises instead of returning `[]`."
        ),
        "difficulty": "easy",
        "category": "linked-list",
        "lines": 1,
        "bug": [
            (
                "ds/ll.py",
                "    while cur is not None:\n        out.append(cur.value)\n        cur = cur.nxt\n    return out",
                "    while cur.nxt is not None:\n        out.append(cur.value)\n        cur = cur.nxt\n    return out",
            )
        ],
        "fail_to_pass": [
            "tests/test_ll.py::test_to_list_empty",
            "tests/test_ll.py::test_to_list_single",
            "tests/test_ll.py::test_from_seq_order",
        ],
        "pass_to_pass": [
            "tests/test_ll.py::test_length_empty",
            "tests/test_ll.py::test_length_three",
            "tests/test_ll.py::test_reverse_empty",
        ],
    },
    {
        "id": "ds-03",
        "instruction": (
            "Calling `pop()` on an empty `Stack` (in `ds/stack.py`) crashes with an "
            "`AttributeError` instead of raising `IndexError`. The empty-stack guard is "
            "missing, so the code dereferences the head even when the stack has no "
            "elements. Popping a non-empty stack is unaffected."
        ),
        "difficulty": "easy",
        "category": "stack",
        "lines": 3,
        "bug": [
            (
                "ds/stack.py",
                '        if self._head is None:\n            raise IndexError("pop from empty stack")\n        item = self._head.value\n        self._head = self._head.nxt\n        return item',
                "        item = self._head.value\n        self._head = self._head.nxt\n        return item",
            )
        ],
        "fail_to_pass": [
            "tests/test_stack_ring.py::test_stack_pop_empty_raises",
        ],
        "pass_to_pass": [
            "tests/test_stack_ring.py::test_stack_push_pop",
            "tests/test_stack_ring.py::test_stack_peek",
            "tests/test_stack_ring.py::test_stack_len",
        ],
    },
    {
        "id": "ds-04",
        "instruction": (
            "`ds/tree.py::height` reports a single-node tree as height 0 and a balanced "
            "two-level tree as height 1. Leaves are treated as zero-height, so every "
            "non-empty tree comes out one level too short. The empty tree is unaffected."
        ),
        "difficulty": "easy",
        "category": "tree",
        "lines": 3,
        "bug": [
            (
                "ds/tree.py",
                "    if node is None:\n        return 0\n    return 1 + max(height(node.left), height(node.right))",
                "    if node is None:\n        return 0\n    if node.left is None and node.right is None:\n        return 0\n    return 1 + max(height(node.left), height(node.right))",
            )
        ],
        "fail_to_pass": [
            "tests/test_lru_tree.py::test_tree_height_single",
            "tests/test_lru_tree.py::test_tree_height_balanced",
            "tests/test_lru_tree.py::test_tree_height_unbalanced",
            "tests/test_lru_tree.py::test_tree_height_skewed_right",
        ],
        "pass_to_pass": [
            "tests/test_lru_tree.py::test_tree_height_empty",
            "tests/test_ll.py::test_length_three",
            "tests/test_lru_tree.py::test_counter_increment",
        ],
    },
    {
        "id": "ds-05",
        "instruction": (
            "`ds/ll.py::append` does not actually add the new node to an existing "
            "(non-empty) list. The new value is created but never linked to the tail, so "
            "the returned list is unchanged and the appended value is lost. Appending to "
            "an empty list still works."
        ),
        "difficulty": "medium",
        "category": "linked-list",
        "lines": 1,
        "bug": [
            (
                "ds/ll.py",
                "    cur = head\n    while cur.nxt is not None:\n        cur = cur.nxt\n    cur.nxt = Node(value)\n    return head",
                "    cur = head\n    while cur.nxt is not None:\n        cur = cur.nxt\n    cur = Node(value)\n    return head",
            )
        ],
        "fail_to_pass": [
            "tests/test_ll.py::test_append_to_existing",
            "tests/test_ll.py::test_append_single_element_list",
        ],
        "pass_to_pass": [
            "tests/test_ll.py::test_append_to_empty",
            "tests/test_ll.py::test_length_three",
            "tests/test_ll.py::test_reverse_three",
        ],
    },
    {
        "id": "ds-06",
        "instruction": (
            "`ds/ll.py::reverse` loses the last node when reversing a list. Reversing "
            "`[1, 2, 3]` yields `[2, 1]` instead of `[3, 2, 1]`, and reversing a "
            "single-element list yields an empty list. The traversal stops one node too "
            "early, so the final node is never linked into the reversed list."
        ),
        "difficulty": "hard",
        "category": "linked-list",
        "lines": 1,
        "bug": [
            (
                "ds/ll.py",
                "    while cur is not None:\n        nxt = cur.nxt\n        cur.nxt = prev\n        prev = cur\n        cur = nxt\n    return prev",
                "    while cur.nxt is not None:\n        nxt = cur.nxt\n        cur.nxt = prev\n        prev = cur\n        cur = nxt\n    return prev",
            )
        ],
        "fail_to_pass": [
            "tests/test_ll.py::test_reverse_single",
            "tests/test_ll.py::test_reverse_three",
            "tests/test_ll.py::test_reverse_four",
        ],
        "pass_to_pass": [
            "tests/test_ll.py::test_length_three",
            "tests/test_ll.py::test_from_seq_order",
            "tests/test_ll.py::test_append_to_existing",
        ],
    },
    {
        "id": "ds-07",
        "instruction": (
            "In `ds/lru.py`, `get()` returns the right value but does not mark the key as "
            "most-recently-used. As a result a subsequent `put()` may evict a key that "
            "was just read, dropping a recently-accessed entry from the cache."
        ),
        "difficulty": "medium",
        "category": "cache",
        "lines": 3,
        "bug": [
            (
                "ds/lru.py",
                "        value = self._cache.pop(key)\n        self._cache[key] = value\n        self.hits.increment()\n        return value",
                "        self.hits.increment()\n        return self._cache[key]",
            )
        ],
        "fail_to_pass": [
            "tests/test_lru_tree.py::test_lru_evicts_least_recently_used",
        ],
        "pass_to_pass": [
            "tests/test_lru_tree.py::test_lru_get_missing",
            "tests/test_lru_tree.py::test_lru_put_get",
            "tests/test_lru_tree.py::test_lru_update_existing",
        ],
    },
    {
        "id": "ds-08",
        "instruction": (
            "The LRU cache's hit/miss statistics are always zero after a few `get()` "
            "calls. The counters are kept in `ds/counter.py` and updated from "
            "`ds/lru.py`, and both ends are wrong: the counter's default increment is "
            "zero, and a cache miss is recorded against the hit counter."
        ),
        "difficulty": "hard",
        "category": "cache",
        "lines": 3,
        "bug": [
            (
                "ds/counter.py",
                '    def increment(self, n=1):\n        """Add ``n`` to the counter and return the new value."""\n        with self._lock:\n            self._value += n\n        return self._value',
                '    def increment(self, n=0):\n        """Add ``n`` to the counter and return the new value."""\n        with self._lock:\n            self._value += n\n        return self._value',
            ),
            (
                "ds/lru.py",
                "        if key not in self._cache:\n            self.misses.increment()\n            return -1",
                "        if key not in self._cache:\n            self.hits.increment()\n            return -1",
            ),
        ],
        "fail_to_pass": [
            "tests/test_lru_tree.py::test_lru_hit_miss_counts",
        ],
        "pass_to_pass": [
            "tests/test_lru_tree.py::test_lru_get_missing",
            "tests/test_lru_tree.py::test_lru_put_get",
            "tests/test_lru_tree.py::test_lru_evicts_least_recently_used",
        ],
    },
    {
        "id": "ds-09",
        "instruction": (
            "`ds/lru.py::put` evicts the wrong entry when the cache is full: it removes "
            "the most-recently-used key instead of the least-recently-used one, so the "
            "key written most recently is the first to be dropped."
        ),
        "difficulty": "medium",
        "category": "cache",
        "lines": 1,
        "bug": [
            (
                "ds/lru.py",
                "        if key in self._cache:\n            self._cache.pop(key)\n        elif len(self._cache) >= self.capacity:\n            self._cache.popitem(last=False)\n        self._cache[key] = value",
                "        if key in self._cache:\n            self._cache.pop(key)\n        elif len(self._cache) >= self.capacity:\n            self._cache.popitem(last=True)\n        self._cache[key] = value",
            )
        ],
        "fail_to_pass": [
            "tests/test_lru_tree.py::test_lru_evicts_oldest",
            "tests/test_lru_tree.py::test_lru_evicts_least_recently_used",
        ],
        "pass_to_pass": [
            "tests/test_lru_tree.py::test_lru_put_get",
            "tests/test_lru_tree.py::test_lru_update_existing",
            "tests/test_lru_tree.py::test_lru_len_and_contains",
        ],
    },
    {
        "id": "ds-10",
        "instruction": (
            "`ds/ring.py::RingBuffer.push` crashes with an `IndexError` once the buffer "
            "has wrapped around (after some pops). The write index is computed without "
            "wrapping modulo the capacity, so it falls outside the backing array when the "
            "head has advanced."
        ),
        "difficulty": "medium",
        "category": "ring-buffer",
        "lines": 1,
        "bug": [
            (
                "ds/ring.py",
                "        tail = (self._head + self._size) % self._capacity\n        self._buf[tail] = item\n        self._size += 1",
                "        tail = self._head + self._size\n        self._buf[tail] = item\n        self._size += 1",
            )
        ],
        "fail_to_pass": [
            "tests/test_stack_ring.py::test_ring_wraparound",
            "tests/test_stack_ring.py::test_ring_wraparound_order",
        ],
        "pass_to_pass": [
            "tests/test_stack_ring.py::test_ring_push_pop",
            "tests/test_stack_ring.py::test_ring_full",
            "tests/test_stack_ring.py::test_ring_peek",
        ],
    },
    {
        "id": "ds-11",
        "instruction": (
            "`ds/ring.py::RingBuffer.to_list` returns elements in the wrong order after "
            "the buffer has wrapped around. It reads from index 0 instead of from the "
            "current head, so the oldest slot is reported first even when newer data "
            "should come first."
        ),
        "difficulty": "medium",
        "category": "ring-buffer",
        "lines": 1,
        "bug": [
            (
                "ds/ring.py",
                "        for i in range(self._size):\n            out.append(self._buf[(self._head + i) % self._capacity])",
                "        for i in range(self._size):\n            out.append(self._buf[i])",
            )
        ],
        "fail_to_pass": [
            "tests/test_stack_ring.py::test_ring_wraparound",
            "tests/test_stack_ring.py::test_ring_wraparound_order",
        ],
        "pass_to_pass": [
            "tests/test_stack_ring.py::test_ring_push_pop",
            "tests/test_stack_ring.py::test_ring_peek",
            "tests/test_stack_ring.py::test_ring_len",
        ],
    },
    {
        "id": "ds-12",
        "instruction": (
            "The public `ds` package API for linked lists is broken. `ds.from_seq` builds "
            "lists in the wrong order and `ds.to_list` is missing from the package, so "
            "round-tripping a sequence through `ds.to_list(ds.from_seq(...))` fails."
        ),
        "difficulty": "hard",
        "category": "api",
        "lines": 3,
        "bug": [
            (
                "ds/ll.py",
                "    for item in reversed(seq):\n        head = Node(item, head)",
                "    for item in seq:\n        head = Node(item, head)",
            ),
            (
                "ds/__init__.py",
                "from ds.ll import Node, append, from_seq, length, reverse, to_list",
                "from ds.ll import Node, append, from_seq, length, reverse",
            ),
        ],
        "fail_to_pass": [
            "tests/test_ll.py::test_api_from_seq_to_list_roundtrip",
        ],
        "pass_to_pass": [
            "tests/test_ll.py::test_length_three",
            "tests/test_ll.py::test_to_list_single",
            "tests/test_ll.py::test_length_empty",
        ],
    },
    {
        "id": "ds-13",
        "instruction": (
            "`ds/counter.py::Counter.increment` loses updates under concurrent use. It "
            "performs a read-modify-write without holding the lock: it reads the current "
            "value, yields, then writes the incremented value back, so when multiple "
            "threads call `increment()` at the same time the final value ends up lower "
            "than the total number of increments."
        ),
        "difficulty": "hard",
        "category": "concurrency",
        "lines": 3,
        "bug": [
            (
                "ds/counter.py",
                '    def increment(self, n=1):\n        """Add ``n`` to the counter and return the new value."""\n        with self._lock:\n            self._value += n\n        return self._value',
                '    def increment(self, n=1):\n        """Add ``n`` to the counter and return the new value."""\n        current = self._value\n        current += n\n        time.sleep(0)\n        self._value = current\n        return self._value',
            )
        ],
        "fail_to_pass": [
            "tests/test_lru_tree.py::test_counter_concurrent_increment",
        ],
        "pass_to_pass": [
            "tests/test_lru_tree.py::test_counter_increment",
            "tests/test_lru_tree.py::test_counter_increment_by_n",
            "tests/test_lru_tree.py::test_counter_reset",
        ],
    },
]
