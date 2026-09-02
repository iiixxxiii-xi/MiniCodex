"""Small numeric/statistics library (intentionally buggy for eval tasks)."""


def mean(values):
    """Return the arithmetic mean of ``values``."""
    if not values:
        raise ValueError("mean of empty sequence")
    return sum(values) / len(values)


def median(values):
    """Return the median of ``values``."""
    s = sorted(values)
    n = len(s)
    if n % 2 == 0:
        return (s[n // 2 - 1] + s[n // 2]) / 2
    return s[n // 2]


def mode(values):
    """Return the most frequent value in ``values``."""
    return max(set(values), key=values.count)


def variance(values):
    """Return the sample variance of ``values``."""
    m = sum(values) / len(values)
    return sum((x - m) ** 2 for x in values) / (len(values) - 1)


def percentile(values, p):
    """Return the ``p``-th percentile (0-100) of ``values``."""
    s = sorted(values)
    idx = min(int(len(s) * p / 100), len(s) - 1)
    return s[idx]


def moving_average(values, window):
    """Return the moving average of ``values`` over ``window``."""
    return [sum(values[i:i + window]) / window for i in range(len(values) - window + 1)]


def clamp(value, lo, hi):
    """Clamp ``value`` to the inclusive range [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def fibonacci(n):
    """Return the n-th Fibonacci number (fib(0)=0, fib(1)=1)."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def is_prime(n):
    """Return True if ``n`` is prime."""
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True


def gcd(a, b):
    """Return the greatest common divisor of ``a`` and ``b``."""
    while b:
        a, b = b, a % b
    return b
