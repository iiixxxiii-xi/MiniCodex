"""Retry policy: decide whether a failed task should retry."""
from scheduler.task import Task


def should_retry(task: Task) -> bool:
    if task.failures >= task.max_retries:
        return False
    task.failures += 1
    return True
