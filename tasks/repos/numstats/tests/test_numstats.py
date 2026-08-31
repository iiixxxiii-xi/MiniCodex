import pytest

import numstats


def test_mean():
    assert numstats.mean([1, 2, 3, 4]) == 2.5
    with pytest.raises(ValueError):
        numstats.mean([])


def test_median():
    assert numstats.median([1, 2, 3, 4]) == 2.5
    assert numstats.median([1, 2, 3]) == 2


def test_mode():
    assert numstats.mode([1, 1, 2, 3]) == 1
    assert numstats.mode(["a", "b", "a"]) == "a"


def test_variance():
    assert abs(numstats.variance([1, 2, 3, 4]) - 5 / 3) < 1e-9


def test_percentile():
    assert numstats.percentile([1, 2, 3, 4, 5], 50) == 3
    assert numstats.percentile([1, 2, 3, 4, 5], 100) == 5


def test_moving_average():
    assert numstats.moving_average([1, 2, 3, 4, 5], 3) == [2.0, 3.0, 4.0]


def test_clamp():
    assert numstats.clamp(0, 1, 10) == 1
    assert numstats.clamp(50, 1, 10) == 10
    assert numstats.clamp(5, 1, 10) == 5


def test_fibonacci():
    assert numstats.fibonacci(0) == 0
    assert numstats.fibonacci(1) == 1
    assert numstats.fibonacci(6) == 8


def test_is_prime():
    assert numstats.is_prime(1) is False
    assert numstats.is_prime(2) is True
    assert numstats.is_prime(4) is False
    assert numstats.is_prime(17) is True


def test_gcd():
    assert numstats.gcd(48, 18) == 6
    assert numstats.gcd(0, 5) == 5
