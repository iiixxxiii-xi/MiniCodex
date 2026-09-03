"""Series operations: moving averages, rolling statistics and subarray sums."""

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
