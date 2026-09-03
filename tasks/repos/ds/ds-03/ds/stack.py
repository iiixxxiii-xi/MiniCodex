"""A last-in-first-out stack backed by a singly linked list."""

from ds.ll import Node


class Stack:
    """A simple stack supporting push/pop/peek and len()."""

    def __init__(self):
        self._head = None

    def push(self, item):
        self._head = Node(item, self._head)

    def pop(self):
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
