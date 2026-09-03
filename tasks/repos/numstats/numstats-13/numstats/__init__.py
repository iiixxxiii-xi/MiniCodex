"""numstats: a small numeric/statistics library.

Public API:
- descriptive: mean, median, mode, variance, stdev, percentile
- series: moving_average, rolling_variance, cumulative_sum, max_subarray_sum
- number theory: fibonacci, is_prime, gcd, clamp
- running: RunningStats (online accumulator)
"""

from numstats.descriptive import mean, median, mode, percentile, variance
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
