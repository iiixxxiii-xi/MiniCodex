"""A priority queue of tasks (lower priority value = higher priority)."""
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
