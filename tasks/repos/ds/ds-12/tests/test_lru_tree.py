import threading

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
