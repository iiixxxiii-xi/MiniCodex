"""A least-recently-used cache backed by an ordered dict."""

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
