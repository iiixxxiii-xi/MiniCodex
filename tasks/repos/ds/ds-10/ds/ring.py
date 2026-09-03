"""A fixed-capacity ring buffer (FIFO)."""


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
        tail = self._head + self._size
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
