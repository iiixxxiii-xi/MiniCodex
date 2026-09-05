"""Repo spec: an LRU cache with a cross-module eviction bug."""

REPO = "cache"

FILES = {
    "cache/__init__.py": "",
    "cache/storage.py": '''"""Storage: an in-memory key-value store."""


class Storage:
    def __init__(self):
        self._data = {}

    def get(self, key):
        return self._data.get(key)

    def put(self, key, value):
        self._data[key] = value

    def remove(self, key):
        self._data.pop(key, None)

    def __len__(self):
        return len(self._data)
''',
    "cache/eviction.py": '''"""Eviction: pick which key to drop when the cache is full (LRU)."""


class LRU:
    def __init__(self, capacity):
        self.capacity = capacity
        self._order = []  # most-recently-used at the end

    def touch(self, key):
        if key in self._order:
            self._order.remove(key)
        self._order.append(key)

    def evict(self):
        return self._order.pop(0)

    def remove(self, key):
        if key in self._order:
            self._order.remove(key)
''',
    "cache/cache.py": '''"""Cache: the public get/put API combining storage + LRU eviction."""

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
''',
}

TESTS = {
    "tests/test_cache.py": '''"""Tests for the cache (eviction bug surfaces via get misses)."""

from cache.cache import Cache


def test_cache_hit():
    c = Cache(2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1
    assert c.get("b") == 2


def test_lru_evicts_least_recently_used():
    c = Cache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")          # a is now most recently used
    c.put("c", 3)       # should evict b (least recently used)
    assert c.get("a") == 1
    assert c.get("b") is None
    assert c.get("c") == 3


def test_cache_miss_returns_none():
    c = Cache(1)
    assert c.get("missing") is None
''',
}

TASKS = [
    {
        "id": "cache-lru-eviction",
        "instruction": (
            "Fix the bug in the LRU cache where, after inserting more keys than "
            "the capacity, the cache evicts the wrong entry. The test "
            "'test_lru_evicts_least_recently_used' fails because a recently-used "
            "key disappears instead of the least-recently-used one."
        ),
        "difficulty": "hard",
        "category": "cross-module",
        "lines": 1,
        "bug": [
            ("cache/eviction.py",
             "        return self._order.pop(0)\n",
             "        return self._order.pop()\n"),
        ],
        "fail_to_pass": [
            "tests/test_cache.py::test_lru_evicts_least_recently_used",
        ],
        "pass_to_pass": [
            "tests/test_cache.py::test_cache_hit",
            "tests/test_cache.py::test_cache_miss_returns_none",
        ],
    },
]
