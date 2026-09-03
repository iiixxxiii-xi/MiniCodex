"""Online (incremental) statistics via a running accumulator."""

import threading
import time


class RunningStats:
    """Accumulate values incrementally and report running statistics.

    ``add`` is thread-safe and may be called from multiple threads.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._count = 0
        self._mean = 0.0
        self._m2 = 0.0

    def add(self, value):
        """Incorporate ``value`` into the running statistics."""
        with self._lock:
            self._count += 1
            delta = value - self._mean
            self._mean += delta / self._count
            self._m2 += delta * (value - self._mean)

    def add_all(self, values):
        """Incorporate every value in ``values``."""
        for value in values:
            self.add(value)

    @property
    def count(self):
        return self._count

    @property
    def mean(self):
        return self._mean

    @property
    def variance(self):
        """Sample variance of the values seen so far (0.0 for fewer than two values)."""
        if self._count < 2:
            return 0.0
        return self._m2 / (self._count - 1)
