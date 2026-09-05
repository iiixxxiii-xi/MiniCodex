"""Repo spec: a task scheduler with a cross-module retry-priority bug.

The bug lives in the runner's retry path (a retried task is re-inserted with a
boosted priority), but its symptom surfaces in the *order* tasks complete, which
depends on queue ordering + retry bookkeeping together. A fix must understand
three modules — SWE-bench-Pro difficulty, not a one-line sort flip.
"""

REPO = "scheduler"

FILES = {
    "scheduler/__init__.py": "",
    "scheduler/task.py": '''"""Task model."""
from dataclasses import dataclass


@dataclass
class Task:
    id: str
    priority: int
    max_retries: int = 2
    failures: int = 0
''',
    "scheduler/queue.py": '''"""A priority queue of tasks (lower priority value = higher priority)."""
import heapq


class TaskQueue:
    def __init__(self):
        self._heap = []

    def push(self, task):
        heapq.heappush(self._heap, (task.priority, task.id, task))

    def pop(self):
        if not self._heap:
            return None
        return heapq.heappop(self._heap)[2]

    def __len__(self):
        return len(self._heap)
''',
    "scheduler/retry.py": '''"""Retry policy: decide whether a failed task should retry."""
from scheduler.task import Task


def should_retry(task: Task) -> bool:
    if task.failures >= task.max_retries:
        return False
    task.failures += 1
    return True
''',
    "scheduler/runner.py": '''"""Run tasks from the queue, retrying failures."""
from scheduler.retry import should_retry


def run_all(queue, fn):
    """Run every task until it succeeds or exhausts retries.

    Returns the ids of tasks that eventually completed, in completion order.
    """
    completed = []
    while len(queue) > 0:
        task = queue.pop()
        if fn(task):
            completed.append(task.id)
        elif should_retry(task):
            # Re-insert at its original priority so ordering is preserved.
            queue.push(task)
        # else: exhausted retries -> drop the task
    return completed
''',
}

TESTS = {
    "tests/test_scheduler.py": '''from scheduler.task import Task
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
''',
}

TASKS = [
    {
        "id": "scheduler-retry-priority",
        "instruction": (
            "Fix the bug in the task scheduler where a task that fails and is "
            "retried ends up delayed to the very end instead of keeping its "
            "priority position. The test 'test_retry_keeps_original_priority' "
            "fails: task 'a' (priority 5) fails once, but on its retry it runs "
            "after task 'b' (priority 8), which has lower priority. Trace how the "
            "queue orders tasks, how the runner re-inserts a failed task, and how "
            "retry bookkeeping works together to find the root cause."
        ),
        "difficulty": "hard",
        "category": "cross-module",
        "lines": 2,
        "bug": [
            ("scheduler/runner.py",
             "        elif should_retry(task):\n"
             "            # Re-insert at its original priority so ordering is preserved.\n"
             "            queue.push(task)\n",
             "        elif should_retry(task):\n"
             "            # Re-insert at a very low priority so it is retried later.\n"
             "            task.priority = 999\n"
             "            queue.push(task)\n"),
        ],
        "fail_to_pass": [
            "tests/test_scheduler.py::test_retry_keeps_original_priority",
        ],
        "pass_to_pass": [
            "tests/test_scheduler.py::test_priority_order",
            "tests/test_scheduler.py::test_exhausted_retries_drops_task",
        ],
    },
]
