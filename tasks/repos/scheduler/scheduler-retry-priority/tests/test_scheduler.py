from scheduler.task import Task
from scheduler.queue import TaskQueue
from scheduler.runner import run_all


def test_priority_order():
    q = TaskQueue()
    q.push(Task("low", priority=10))
    q.push(Task("high", priority=1))
    q.push(Task("mid", priority=5))
    order = run_all(q, lambda t: True)
    assert order == ["high", "mid", "low"]


def test_retry_keeps_original_priority():
    q = TaskQueue()
    q.push(Task("a", priority=5))
    q.push(Task("b", priority=8))
    calls = {"a": 0}

    def fn(task):
        calls[task.id] = calls.get(task.id, 0) + 1
        return task.id != "a" or calls[task.id] >= 2  # "a" fails its first run

    order = run_all(q, fn)
    # "a" (priority 5) fails once, so on its retry it should still complete
    # before "b" (priority 8). With the bug, "a" is dropped to priority 999 and
    # completes last.
    assert order == ["a", "b"]
    assert calls["a"] == 2


def test_exhausted_retries_drops_task():
    q = TaskQueue()
    q.push(Task("flaky", priority=1, max_retries=1))
    order = run_all(q, lambda t: False)
    assert order == []
