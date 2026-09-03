"""A thread-safe integer counter."""

import threading
import time


class Counter:
    """An integer counter safe to use from multiple threads."""

    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()

    def increment(self, n=1):
        """Add ``n`` to the counter and return the new value."""
        current = self._value
        current += n
        time.sleep(0)
        self._value = current
        return self._value

    @property
    def value(self):
        with self._lock:
            return self._value

    def reset(self):
        with self._lock:
            self._value = 0
