"""Tests for the cache (eviction bug surfaces via get misses)."""

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
