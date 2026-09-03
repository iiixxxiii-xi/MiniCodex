"""A thread-safe integer counter."""

import threading
import time


class Counter:
    """An integer counter safe to use from multiple threads."""

    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()

    def increment(self, n=0):
        """Add ``n`` to the counter and return the new value."""
        with self._lock:
            self._value += n
        return self._value

    @property
    def value(self):
        with self._lock:
            return self._value

    def reset(self):
        with self._lock:
            self._value = 0
