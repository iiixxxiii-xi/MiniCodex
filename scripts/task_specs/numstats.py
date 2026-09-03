"""Repo spec: ``numstats`` — a small multi-module numeric/statistics library.

The library is split across four functional modules — ``descriptive`` (mean /
median / mode / variance / percentile), ``series`` (moving averages, rolling
variance, Kadane max-subarray), ``number_theory`` (fibonacci / is_prime / gcd /
clamp) and ``running`` (an online ``RunningStats`` accumulator) — plus a public
``__init__`` that re-exports the API. ``series`` imports helpers from
``descriptive``, giving real cross-module coupling.

Bugs span one-line logic slips (median even-length, mode tie-breaking, clamp
bounds), algorithmic errors (sample-vs-population variance, percentile
clamping, Kadane initialisation), boundary conditions (empty/single input,
negative `n`, `n < 2` primes, gcd with zero), a thread-safety bug in the
running accumulator, and two cross-file integration bugs (the rolling-variance
flag and the ``stdev`` public-API wiring).
"""

REPO = "numstats"

FILES = {
    "numstats/__init__.py": '''"""numstats: a small numeric/statistics library.

Public API:
- descriptive: mean, median, mode, variance, stdev, percentile
- series: moving_average, rolling_variance, cumulative_sum, max_subarray_sum
- number theory: fibonacci, is_prime, gcd, clamp
- running: RunningStats (online accumulator)
"""

from numstats.descriptive import mean, median, mode, percentile, stdev, variance
from numstats.number_theory import clamp, fibonacci, gcd, is_prime
from numstats.running import RunningStats
from numstats.series import cumulative_sum, max_subarray_sum, moving_average, rolling_variance

__all__ = [
    "mean",
    "median",
    "mode",
    "variance",
    "stdev",
    "percentile",
    "moving_average",
    "rolling_variance",
    "cumulative_sum",
    "max_subarray_sum",
    "fibonacci",
    "is_prime",
    "gcd",
    "clamp",
    "RunningStats",
]
''',
    "numstats/descriptive.py": '''"""Descriptive statistics for sequences of numbers."""

import math


def mean(data):
    """Return the arithmetic mean of ``data``. Raises ValueError on empty input."""
    if len(data) == 0:
        raise ValueError("mean of empty sequence")
    return sum(data) / len(data)


def median(data):
    """Return the median value of ``data`` (average of the two middles for even length)."""
    if len(data) == 0:
        raise ValueError("median of empty sequence")
    ordered = sorted(data)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def mode(data):
    """Return the most frequent value in ``data`` (smallest value wins ties)."""
    if len(data) == 0:
        raise ValueError("mode of empty sequence")
    counts = {}
    for value in data:
        counts[value] = counts.get(value, 0) + 1
    max_count = max(counts.values())
    return min(v for v, c in counts.items() if c == max_count)


def variance(data, sample=True):
    """Return the variance of ``data`` (sample variance by default, population if sample=False)."""
    if len(data) == 0:
        raise ValueError("variance of empty sequence")
    if sample and len(data) < 2:
        raise ValueError("sample variance requires at least two data points")
    m = mean(data)
    ss = sum((x - m) ** 2 for x in data)
    denom = len(data) - 1 if sample else len(data)
    return ss / denom


def stdev(data, sample=True):
    """Return the standard deviation of ``data``."""
    return math.sqrt(variance(data, sample=sample))


def percentile(data, p):
    """Return the p-th percentile of ``data`` (0 <= p <= 100) with linear interpolation."""
    if len(data) == 0:
        raise ValueError("percentile of empty sequence")
    if not (0.0 <= p <= 100.0):
        raise ValueError("p must be between 0 and 100")
    ordered = sorted(data)
    if len(ordered) == 1:
        return ordered[0]
    rank = (p / 100.0) * (len(ordered) - 1)
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return ordered[lower]
    frac = rank - lower
    return ordered[lower] * (1.0 - frac) + ordered[upper] * frac
''',
    "numstats/series.py": '''"""Series operations: moving averages, rolling statistics and subarray sums."""

from numstats.descriptive import mean, variance


def moving_average(data, window):
    """Return the list of ``window``-wide moving averages of ``data``."""
    if window < 1:
        raise ValueError("window must be at least 1")
    if len(data) == 0:
        raise ValueError("moving_average of empty sequence")
    if window > len(data):
        raise ValueError("window larger than data")
    result = []
    for i in range(len(data) - window + 1):
        result.append(mean(data[i:i + window]))
    return result


def rolling_variance(data, window):
    """Return the list of ``window``-wide rolling sample variances of ``data``."""
    if window < 2:
        raise ValueError("window must be at least 2 for variance")
    if len(data) == 0:
        raise ValueError("rolling_variance of empty sequence")
    if window > len(data):
        raise ValueError("window larger than data")
    result = []
    for i in range(len(data) - window + 1):
        result.append(variance(data[i:i + window]))
    return result


def cumulative_sum(data):
    """Return the cumulative sums of ``data``."""
    result = []
    total = 0
    for value in data:
        total += value
        result.append(total)
    return result


def max_subarray_sum(data):
    """Return the maximum sum of any contiguous subarray (Kadane's algorithm)."""
    if len(data) == 0:
        raise ValueError("max_subarray_sum of empty sequence")
    best = current = data[0]
    for value in data[1:]:
        current = max(value, current + value)
        best = max(best, current)
    return best
''',
    "numstats/number_theory.py": '''"""Number-theoretic utilities."""


def fibonacci(n):
    """Return the n-th Fibonacci number (F0=0, F1=1); n must be a non-negative int."""
    if not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 0:
        raise ValueError("n must be non-negative")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def is_prime(n):
    """Return True if ``n`` is prime; ``n`` must be a non-negative integer (0 and 1 are not prime)."""
    if not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def gcd(a, b):
    """Return the greatest common divisor of ``a`` and ``b`` (non-negative integers)."""
    a, b = abs(a), abs(b)
    while b != 0:
        a, b = b, a % b
    return a


def clamp(value, lo, hi):
    """Return ``value`` clamped to the inclusive interval [lo, hi]."""
    if lo > hi:
        raise ValueError("lo must be <= hi")
    return max(lo, min(hi, value))
''',
    "numstats/running.py": '''"""Online (incremental) statistics via a running accumulator."""

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
''',
}

TESTS = {
    "tests/test_descriptive.py": '''import pytest

import numstats
from numstats.descriptive import mean, median, mode, percentile, stdev, variance


def test_mean_empty():
    with pytest.raises(ValueError):
        mean([])


def test_mean_basic():
    assert mean([1, 2, 3, 4]) == 2.5


def test_mean_single():
    assert mean([7]) == 7


def test_mean_all_negative():
    assert mean([-1, -2, -3]) == -2


def test_median_empty():
    with pytest.raises(ValueError):
        median([])


def test_median_odd():
    assert median([3, 1, 2]) == 2


def test_median_even():
    assert median([1, 2, 3, 4]) == 2.5


def test_median_even_two():
    assert median([10, 20]) == 15


def test_median_single():
    assert median([5]) == 5


def test_median_unsorted():
    assert median([4, 1, 3, 2]) == 2.5


def test_mode_empty():
    with pytest.raises(ValueError):
        mode([])


def test_mode_basic():
    assert mode([1, 2, 2, 3]) == 2


def test_mode_single():
    assert mode([9]) == 9


def test_mode_ties_smallest():
    assert mode([3, 1, 3, 1]) == 1


def test_variance_empty():
    with pytest.raises(ValueError):
        variance([])


def test_variance_sample():
    assert variance([1, 2, 3, 4]) == pytest.approx(1.6666666666666667)


def test_variance_population():
    assert variance([1, 2, 3, 4], sample=False) == pytest.approx(1.25)


def test_variance_single_sample_raises():
    with pytest.raises(ValueError):
        variance([5])


def test_stdev_sample():
    assert stdev([1, 2, 3, 4]) == pytest.approx(1.2909944487358056)


def test_percentile_empty():
    with pytest.raises(ValueError):
        percentile([], 50)


def test_percentile_p0():
    assert percentile([3, 1, 2, 4], 0) == 1


def test_percentile_p100():
    assert percentile([3, 1, 2, 4], 100) == 4


def test_percentile_median():
    assert percentile([1, 2, 3, 4], 50) == pytest.approx(2.5)


def test_percentile_single():
    assert percentile([42], 99) == 42


def test_percentile_out_of_range():
    with pytest.raises(ValueError):
        percentile([1, 2, 3], 101)


def test_api_mean():
    assert numstats.mean([1, 2, 3, 4]) == 2.5


def test_api_stdev():
    assert numstats.stdev([1, 2, 3, 4]) == pytest.approx(1.2909944487358056)


def test_api_running_stats():
    stats = numstats.RunningStats()
    stats.add_all([1, 2, 3, 4])
    assert stats.mean == pytest.approx(2.5)
''',
    "tests/test_series.py": '''import threading

import pytest

from numstats.running import RunningStats
from numstats.series import cumulative_sum, max_subarray_sum, moving_average, rolling_variance


def test_moving_average_basic():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]


def test_moving_average_window_one():
    assert moving_average([1, 2, 3], 1) == [1, 2, 3]


def test_moving_average_full_window():
    assert moving_average([1, 2, 3], 3) == [2]


def test_moving_average_empty():
    with pytest.raises(ValueError):
        moving_average([], 2)


def test_moving_average_window_too_small():
    with pytest.raises(ValueError):
        moving_average([1, 2, 3], 0)


def test_moving_average_window_too_large():
    with pytest.raises(ValueError):
        moving_average([1, 2, 3], 4)


def test_rolling_variance_basic():
    assert rolling_variance([1, 2, 3, 4], 3) == pytest.approx([1.0, 1.0])


def test_rolling_variance_window_too_small():
    with pytest.raises(ValueError):
        rolling_variance([1, 2, 3], 1)


def test_cumulative_sum_basic():
    assert cumulative_sum([1, 2, 3, 4]) == [1, 3, 6, 10]


def test_cumulative_sum_empty():
    assert cumulative_sum([]) == []


def test_max_subarray_sum_basic():
    assert max_subarray_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6


def test_max_subarray_sum_all_negative():
    assert max_subarray_sum([-3, -1, -2]) == -1


def test_max_subarray_sum_single():
    assert max_subarray_sum([5]) == 5


def test_max_subarray_sum_empty():
    with pytest.raises(ValueError):
        max_subarray_sum([])


def test_running_stats_mean():
    stats = RunningStats()
    for x in [1, 2, 3, 4]:
        stats.add(x)
    assert stats.count == 4
    assert stats.mean == pytest.approx(2.5)


def test_running_stats_variance():
    stats = RunningStats()
    for x in [1, 2, 3, 4]:
        stats.add(x)
    assert stats.variance == pytest.approx(1.6666666666666667)


def test_running_stats_empty():
    stats = RunningStats()
    assert stats.count == 0
    assert stats.variance == 0.0


def test_running_stats_add_all():
    stats = RunningStats()
    stats.add_all([1, 2, 3, 4])
    assert stats.count == 4
    assert stats.mean == pytest.approx(2.5)


def test_running_stats_concurrent_updates():
    stats = RunningStats()
    n_threads = 8
    per_thread = 2000
    barrier = threading.Barrier(n_threads)

    def worker(thread_id):
        barrier.wait()
        for i in range(per_thread):
            stats.add(float(thread_id * per_thread + i))

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert stats.count == n_threads * per_thread
''',
    "tests/test_number_theory.py": '''import pytest

from numstats.number_theory import clamp, fibonacci, gcd, is_prime


def test_fibonacci_zero():
    assert fibonacci(0) == 0


def test_fibonacci_one():
    assert fibonacci(1) == 1


def test_fibonacci_ten():
    assert fibonacci(10) == 55


def test_fibonacci_negative():
    with pytest.raises(ValueError):
        fibonacci(-1)


def test_fibonacci_non_int():
    with pytest.raises(TypeError):
        fibonacci(2.5)


def test_is_prime_zero():
    assert is_prime(0) is False


def test_is_prime_one():
    assert is_prime(1) is False


def test_is_prime_two():
    assert is_prime(2) is True


def test_is_prime_three():
    assert is_prime(3) is True


def test_is_prime_four():
    assert is_prime(4) is False


def test_is_prime_large_prime():
    assert is_prime(97) is True


def test_is_prime_large_composite():
    assert is_prime(100) is False


def test_is_prime_negative():
    assert is_prime(-7) is False


def test_gcd_basic():
    assert gcd(12, 18) == 6


def test_gcd_zero():
    assert gcd(0, 5) == 5


def test_gcd_zero_second():
    assert gcd(5, 0) == 5


def test_gcd_zero_zero():
    assert gcd(0, 0) == 0


def test_gcd_negative():
    assert gcd(-12, 18) == 6


def test_clamp_below():
    assert clamp(-5, 0, 5) == 0


def test_clamp_above():
    assert clamp(10, 0, 5) == 5


def test_clamp_in_range():
    assert clamp(3, 0, 5) == 3


def test_clamp_invalid():
    with pytest.raises(ValueError):
        clamp(1, 5, 0)
''',
}

TASKS = [
    {
        "id": "numstats-01",
        "instruction": (
            "Fix `mean` in `numstats/descriptive.py` so it raises a `ValueError` when given an "
            "empty sequence. `mean([])` currently crashes with a `ZeroDivisionError` instead of "
            "reporting the empty-input error."
        ),
        "difficulty": "easy",
        "category": "descriptive",
        "lines": 2,
        "bug": [
            (
                "numstats/descriptive.py",
                '    if len(data) == 0:\n'
                '        raise ValueError("mean of empty sequence")\n'
                "    return sum(data) / len(data)",
                "    return sum(data) / len(data)",
            )
        ],
        "fail_to_pass": [
            "tests/test_descriptive.py::test_mean_empty",
        ],
        "pass_to_pass": [
            "tests/test_descriptive.py::test_mean_basic",
            "tests/test_descriptive.py::test_mean_single",
            "tests/test_descriptive.py::test_mean_all_negative",
        ],
    },
    {
        "id": "numstats-02",
        "instruction": (
            "Fix `median` in `numstats/descriptive.py` so it returns the average of the two middle "
            "values for even-length input. For `[1, 2, 3, 4]` it currently returns `3` instead of "
            "`2.5`."
        ),
        "difficulty": "easy",
        "category": "descriptive",
        "lines": 1,
        "bug": [
            (
                "numstats/descriptive.py",
                '    if n % 2 == 1:\n'
                "        return ordered[mid]\n"
                "    return (ordered[mid - 1] + ordered[mid]) / 2",
                '    if n % 2 == 1:\n'
                "        return ordered[mid]\n"
                "    return ordered[mid]",
            )
        ],
        "fail_to_pass": [
            "tests/test_descriptive.py::test_median_even",
            "tests/test_descriptive.py::test_median_even_two",
        ],
        "pass_to_pass": [
            "tests/test_descriptive.py::test_median_empty",
            "tests/test_descriptive.py::test_median_odd",
            "tests/test_descriptive.py::test_median_single",
        ],
    },
    {
        "id": "numstats-03",
        "instruction": (
            "Fix `mode` in `numstats/descriptive.py` so that when multiple values tie for most "
            "frequent, the smallest value is returned. For `[3, 1, 3, 1]` it currently returns `3` "
            "instead of `1`."
        ),
        "difficulty": "easy",
        "category": "descriptive",
        "lines": 1,
        "bug": [
            (
                "numstats/descriptive.py",
                "    return min(v for v, c in counts.items() if c == max_count)",
                "    return max(v for v, c in counts.items() if c == max_count)",
            )
        ],
        "fail_to_pass": [
            "tests/test_descriptive.py::test_mode_ties_smallest",
        ],
        "pass_to_pass": [
            "tests/test_descriptive.py::test_mode_empty",
            "tests/test_descriptive.py::test_mode_basic",
            "tests/test_descriptive.py::test_mode_single",
        ],
    },
    {
        "id": "numstats-04",
        "instruction": (
            "Fix `clamp` in `numstats/number_theory.py` so values above the upper bound are clamped "
            "to `hi`. `clamp(10, 0, 5)` currently returns `10` instead of `5`."
        ),
        "difficulty": "easy",
        "category": "number theory",
        "lines": 1,
        "bug": [
            (
                "numstats/number_theory.py",
                "    return max(lo, min(hi, value))",
                "    return max(lo, value)",
            )
        ],
        "fail_to_pass": [
            "tests/test_number_theory.py::test_clamp_above",
        ],
        "pass_to_pass": [
            "tests/test_number_theory.py::test_clamp_below",
            "tests/test_number_theory.py::test_clamp_in_range",
            "tests/test_number_theory.py::test_clamp_invalid",
        ],
    },
    {
        "id": "numstats-05",
        "instruction": (
            "Fix `percentile` in `numstats/descriptive.py` so it validates the requested percentile "
            "and raises a `ValueError` when `p` is outside 0..100. `percentile([1, 2, 3], 101)` "
            "currently crashes with an `IndexError` instead of reporting the out-of-range value."
        ),
        "difficulty": "medium",
        "category": "descriptive",
        "lines": 2,
        "bug": [
            (
                "numstats/descriptive.py",
                '    if not (0.0 <= p <= 100.0):\n'
                '        raise ValueError("p must be between 0 and 100")\n'
                "    ordered = sorted(data)",
                "    ordered = sorted(data)",
            )
        ],
        "fail_to_pass": [
            "tests/test_descriptive.py::test_percentile_out_of_range",
        ],
        "pass_to_pass": [
            "tests/test_descriptive.py::test_percentile_empty",
            "tests/test_descriptive.py::test_percentile_p0",
            "tests/test_descriptive.py::test_percentile_p100",
            "tests/test_descriptive.py::test_percentile_median",
            "tests/test_descriptive.py::test_percentile_single",
        ],
    },
    {
        "id": "numstats-06",
        "instruction": (
            "Fix `variance` in `numstats/descriptive.py` so it uses the correct denominator: "
            "`n - 1` for sample variance and `n` for population variance. The sample and population "
            "denominators are currently swapped."
        ),
        "difficulty": "medium",
        "category": "descriptive",
        "lines": 1,
        "bug": [
            (
                "numstats/descriptive.py",
                "    denom = len(data) - 1 if sample else len(data)\n"
                "    return ss / denom",
                "    denom = len(data) if sample else len(data) - 1\n"
                "    return ss / denom",
            )
        ],
        "fail_to_pass": [
            "tests/test_descriptive.py::test_variance_sample",
            "tests/test_descriptive.py::test_variance_population",
        ],
        "pass_to_pass": [
            "tests/test_descriptive.py::test_variance_empty",
            "tests/test_descriptive.py::test_variance_single_sample_raises",
            "tests/test_descriptive.py::test_mean_basic",
        ],
    },
    {
        "id": "numstats-07",
        "instruction": (
            "Fix `fibonacci` in `numstats/number_theory.py` so it raises a `ValueError` for negative "
            "`n` instead of silently returning `0`."
        ),
        "difficulty": "medium",
        "category": "number theory",
        "lines": 2,
        "bug": [
            (
                "numstats/number_theory.py",
                '    if n < 0:\n'
                '        raise ValueError("n must be non-negative")\n'
                "    a, b = 0, 1",
                "    a, b = 0, 1",
            )
        ],
        "fail_to_pass": [
            "tests/test_number_theory.py::test_fibonacci_negative",
        ],
        "pass_to_pass": [
            "tests/test_number_theory.py::test_fibonacci_zero",
            "tests/test_number_theory.py::test_fibonacci_one",
            "tests/test_number_theory.py::test_fibonacci_ten",
            "tests/test_number_theory.py::test_fibonacci_non_int",
        ],
    },
    {
        "id": "numstats-08",
        "instruction": (
            "Fix `is_prime` in `numstats/number_theory.py` so `0` and `1` are reported as non-prime. "
            "`is_prime(1)` currently returns `True`."
        ),
        "difficulty": "medium",
        "category": "number theory",
        "lines": 1,
        "bug": [
            (
                "numstats/number_theory.py",
                "    if n < 2:\n"
                "        return False",
                "    if n < 2:\n"
                "        return True",
            )
        ],
        "fail_to_pass": [
            "tests/test_number_theory.py::test_is_prime_zero",
            "tests/test_number_theory.py::test_is_prime_one",
        ],
        "pass_to_pass": [
            "tests/test_number_theory.py::test_is_prime_two",
            "tests/test_number_theory.py::test_is_prime_three",
            "tests/test_number_theory.py::test_is_prime_four",
            "tests/test_number_theory.py::test_is_prime_large_prime",
            "tests/test_number_theory.py::test_is_prime_large_composite",
        ],
    },
    {
        "id": "numstats-09",
        "instruction": (
            "Fix `gcd` in `numstats/number_theory.py` so that `gcd(0, x)` and `gcd(x, 0)` return `x` "
            "rather than `0`. The current code short-circuits any input containing a zero to `0`."
        ),
        "difficulty": "medium",
        "category": "number theory",
        "lines": 3,
        "bug": [
            (
                "numstats/number_theory.py",
                "    a, b = abs(a), abs(b)\n"
                "    while b != 0:\n"
                "        a, b = b, a % b\n"
                "    return a",
                "    a, b = abs(a), abs(b)\n"
                "    if a == 0 or b == 0:\n"
                "        return 0\n"
                "    while b != 0:\n"
                "        a, b = b, a % b\n"
                "    return a",
            )
        ],
        "fail_to_pass": [
            "tests/test_number_theory.py::test_gcd_zero",
            "tests/test_number_theory.py::test_gcd_zero_second",
        ],
        "pass_to_pass": [
            "tests/test_number_theory.py::test_gcd_zero_zero",
            "tests/test_number_theory.py::test_gcd_basic",
            "tests/test_number_theory.py::test_gcd_negative",
        ],
    },
    {
        "id": "numstats-10",
        "instruction": (
            "Fix `rolling_variance` in `numstats/series.py` so it reports the sample variance of each "
            "window. It currently reports population variance because the sample/population flag is "
            "wrong in both `rolling_variance` and the `variance` helper it depends on in "
            "`numstats/descriptive.py`."
        ),
        "difficulty": "hard",
        "category": "series",
        "lines": 2,
        "bug": [
            (
                "numstats/descriptive.py",
                "def variance(data, sample=True):",
                "def variance(data, sample=False):",
            ),
            (
                "numstats/series.py",
                "        result.append(variance(data[i:i + window]))",
                "        result.append(variance(data[i:i + window], sample=False))",
            ),
        ],
        "fail_to_pass": [
            "tests/test_series.py::test_rolling_variance_basic",
        ],
        "pass_to_pass": [
            "tests/test_series.py::test_rolling_variance_window_too_small",
            "tests/test_series.py::test_moving_average_basic",
            "tests/test_descriptive.py::test_variance_population",
        ],
    },
    {
        "id": "numstats-11",
        "instruction": (
            "Fix `max_subarray_sum` in `numstats/series.py` so it returns the correct result for "
            "all-negative input. `max_subarray_sum([-3, -1, -2])` currently returns `0` instead of "
            "`-1`."
        ),
        "difficulty": "hard",
        "category": "series",
        "lines": 2,
        "bug": [
            (
                "numstats/series.py",
                "    best = current = data[0]\n"
                "    for value in data[1:]:",
                "    best = current = 0\n"
                "    for value in data:",
            )
        ],
        "fail_to_pass": [
            "tests/test_series.py::test_max_subarray_sum_all_negative",
        ],
        "pass_to_pass": [
            "tests/test_series.py::test_max_subarray_sum_basic",
            "tests/test_series.py::test_max_subarray_sum_single",
            "tests/test_series.py::test_max_subarray_sum_empty",
        ],
    },
    {
        "id": "numstats-12",
        "instruction": (
            "Fix `RunningStats.add` in `numstats/running.py` so concurrent updates from multiple "
            "threads are not lost. Feeding `N` threads `K` values each should leave the accumulator "
            "with exactly `N * K` values."
        ),
        "difficulty": "hard",
        "category": "running",
        "lines": 6,
        "bug": [
            (
                "numstats/running.py",
                "        with self._lock:\n"
                "            self._count += 1\n"
                "            delta = value - self._mean\n"
                "            self._mean += delta / self._count\n"
                "            self._m2 += delta * (value - self._mean)",
                "        n = self._count\n"
                "        time.sleep(0)\n"
                "        self._count = n + 1\n"
                "        delta = value - self._mean\n"
                "        self._mean += delta / self._count\n"
                "        self._m2 += delta * (value - self._mean)",
            )
        ],
        "fail_to_pass": [
            "tests/test_series.py::test_running_stats_concurrent_updates",
        ],
        "pass_to_pass": [
            "tests/test_series.py::test_running_stats_mean",
            "tests/test_series.py::test_running_stats_variance",
            "tests/test_series.py::test_running_stats_empty",
            "tests/test_series.py::test_running_stats_add_all",
        ],
    },
    {
        "id": "numstats-13",
        "instruction": (
            "Fix the public API so `numstats.stdev` exists and returns the standard deviation. "
            "`numstats.stdev` is currently missing from the package's re-exports, and the underlying "
            "`stdev` in `numstats/descriptive.py` returns the variance (the square root is missing)."
        ),
        "difficulty": "hard",
        "category": "api",
        "lines": 2,
        "bug": [
            (
                "numstats/descriptive.py",
                "    return math.sqrt(variance(data, sample=sample))",
                "    return variance(data, sample=sample)",
            ),
            (
                "numstats/__init__.py",
                "from numstats.descriptive import mean, median, mode, percentile, stdev, variance",
                "from numstats.descriptive import mean, median, mode, percentile, variance",
            ),
        ],
        "fail_to_pass": [
            "tests/test_descriptive.py::test_api_stdev",
        ],
        "pass_to_pass": [
            "tests/test_descriptive.py::test_api_mean",
            "tests/test_descriptive.py::test_api_running_stats",
        ],
    },
]
