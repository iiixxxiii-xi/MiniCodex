"""Small data-structure library (intentionally buggy for eval tasks)."""


class Node:
    def __init__(self, value):
        self.value = value
        self.next = None


class TreeNode:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None


def linked_list_len(head):
    """Return the number of nodes in a linked list."""
    count = 0
    while head is not None:
        count += 1
        head = head.next
    return count


def linked_list_append(head, value):
    """Append ``value`` to the end of a linked list and return the head."""
    new = Node(value)
    if head is None:
        return new
    cur = head
    while cur.next is not None:
        cur = cur.next
    cur.next = new
    return head


def linked_list_reverse(head):
    """Reverse a linked list in place and return the new head."""
    prev = None
    cur = head
    while cur is not None:
        nxt = cur.next
        cur.next = prev
        prev = cur
        cur = nxt
    return prev


def stack_push(stack, value):
    """Push ``value`` onto ``stack`` (a list) and return the stack."""
    stack.append(value)
    return stack


def stack_pop(stack):
    """Pop the top of ``stack``, raising IndexError when empty."""
    if not stack:
        raise IndexError("pop from empty stack")
    return stack.pop()


def stack_peek(stack):
    """Return the top of ``stack`` without removing it, raising IndexError when empty."""
    if not stack:
        raise IndexError("peek from empty stack")
    return stack[-1]


class RingBuffer:
    def __init__(self, capacity):
        self.capacity = capacity
        self.buf = [None] * capacity
        self.head = 0
        self.size = 0

    def push(self, value):
        tail = (self.head + self.size) % self.capacity
        self.buf[tail] = value
        if self.size < self.capacity:
            self.size += 1
        else:
            self.head = (self.head + 1) % self.capacity

    def to_list(self):
        return [self.buf[(self.head + i) % self.capacity] for i in range(self.size)]


class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self._items = {}
        self._order = []

    def get(self, key):
        if key not in self._items:
            return -1
        return self._items[key]

    def put(self, key, value):
        if key in self._items:
            self._order.remove(key)
        self._items[key] = value
        self._order.append(key)
        if len(self._items) > self.capacity:
            evict = self._order.pop(0)
            del self._items[evict]


def binary_tree_height(root):
    """Return the height of a binary tree (0 for an empty tree)."""
    if root is None:
        return 0
    return 1 + max(binary_tree_height(root.left), binary_tree_height(root.right))
