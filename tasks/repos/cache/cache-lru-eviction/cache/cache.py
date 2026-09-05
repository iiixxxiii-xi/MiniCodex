"""Cache: the public get/put API combining storage + LRU eviction."""

from cache.storage import Storage
from cache.eviction import LRU


class Cache:
    def __init__(self, capacity):
        self.storage = Storage()
        self.lru = LRU(capacity)

    def get(self, key):
        value = self.storage.get(key)
        if value is not None:
            self.lru.touch(key)
        return value

    def put(self, key, value):
        self.storage.put(key, value)
        self.lru.touch(key)
        if len(self.storage) > self.lru.capacity:
            victim = self.lru.evict()
            self.storage.remove(victim)
