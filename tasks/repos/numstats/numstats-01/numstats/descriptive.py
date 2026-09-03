"""Descriptive statistics for sequences of numbers."""

import math


def mean(data):
    """Return the arithmetic mean of ``data``. Raises ValueError on empty input."""
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
