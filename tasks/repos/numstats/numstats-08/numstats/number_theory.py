"""Number-theoretic utilities."""


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
        return True
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
