import pytest

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
