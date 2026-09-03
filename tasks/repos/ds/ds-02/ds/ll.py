"""A singly linked list.

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
    while cur.nxt is not None:
        out.append(cur.value)
        cur = cur.nxt
    return out
