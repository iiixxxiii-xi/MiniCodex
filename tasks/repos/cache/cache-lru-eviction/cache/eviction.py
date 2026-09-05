"""Eviction: pick which key to drop when the cache is full (LRU)."""


class LRU:
    def __init__(self, capacity):
        self.capacity = capacity
        self._order = []  # most-recently-used at the end

    def touch(self, key):
        if key in self._order:
            self._order.remove(key)
        self._order.append(key)

    def evict(self):
        return self._order.pop()

    def remove(self, key):
        if key in self._order:
            self._order.remove(key)
