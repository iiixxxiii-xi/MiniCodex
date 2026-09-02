import pytest

import numstats


def test_mean_empty_raises():
    with pytest.raises(ValueError):
        numstats.mean([])


def test_mean_empty_raises_message():
    with pytest.raises(ValueError, match="empty"):
        numstats.mean([])


def test_mean_basic():
    assert numstats.mean([1, 2, 3, 4]) == 2.5


def test_median_even():
    assert numstats.median([1, 2, 3, 4]) == 2.5


def test_median_even_two():
    assert numstats.median([1, 2]) == 1.5


def test_median_odd():
    assert numstats.median([1, 2, 3]) == 2


def test_mode_basic():
    assert numstats.mode([1, 1, 2, 3]) == 1


def test_mode_strings():
    assert numstats.mode(["a", "b", "a"]) == "a"


def test_mode_single():
    assert numstats.mode([7]) == 7


def test_variance_basic():
    assert abs(numstats.variance([1, 2, 3, 4]) - 5 / 3) < 1e-9


def test_variance_two():
    assert abs(numstats.variance([1, 2]) - 0.5) < 1e-9


def test_percentile_max():
    assert numstats.percentile([1, 2, 3, 4, 5], 100) == 5


def test_percentile_full():
    assert numstats.percentile([1, 2], 100) == 2


def test_percentile_median():
    assert numstats.percentile([1, 2, 3, 4, 5], 50) == 3


def test_moving_average_basic():
    assert numstats.moving_average([1, 2, 3, 4, 5], 3) == [2.0, 3.0, 4.0]


def test_moving_average_window_two():
    assert numstats.moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]


def test_moving_average_window_one():
    assert numstats.moving_average([1, 2, 3], 1) == [1, 2, 3]


def test_clamp_low():
    assert numstats.clamp(0, 1, 10) == 1


def test_clamp_high():
    assert numstats.clamp(50, 1, 10) == 10


def test_clamp_in_range():
    assert numstats.clamp(5, 1, 10) == 5


def test_fibonacci_zero():
    assert numstats.fibonacci(0) == 0


def test_fibonacci_one():
    assert numstats.fibonacci(1) == 1


def test_fibonacci_nth():
    assert numstats.fibonacci(6) == 8


def test_is_prime_below_two():
    assert numstats.is_prime(1) is False
    assert numstats.is_prime(0) is False


def test_is_prime_negative():
    assert numstats.is_prime(-3) is False


def test_is_prime_two():
    assert numstats.is_prime(2) is True


def test_is_prime_composite_and_prime():
    assert numstats.is_prime(4) is False
    assert numstats.is_prime(17) is True


def test_gcd_basic():
    assert numstats.gcd(48, 18) == 6


def test_gcd_with_zero():
    assert numstats.gcd(0, 5) == 5


def test_gcd_swap():
    assert numstats.gcd(18, 48) == 6
