"""Run tasks from the queue, retrying failures."""
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
            # Re-insert at a very low priority so it is retried later.
            task.priority = 999
            queue.push(task)
        # else: exhausted retries -> drop the task
    return completed
