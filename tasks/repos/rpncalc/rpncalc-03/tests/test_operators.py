import pytest

from rpncalc.operators import apply, precedence, safe_divide


def test_apply_add():
    assert apply("+", 3, 4) == 7


def test_apply_sub():
    assert apply("-", 10, 4) == 6


def test_apply_mul():
    assert apply("*", 3, 4) == 12


def test_apply_div():
    assert apply("/", 12, 4) == 3


def test_apply_div_float():
    assert apply("/", 5, 2) == 2.5


def test_apply_sub_negative_result():
    assert apply("-", 4, 10) == -6


def test_safe_divide_ok():
    assert safe_divide(12, 4) == 3


def test_safe_divide_zero():
    with pytest.raises(ZeroDivisionError):
        safe_divide(1, 0)


def test_precedence_mul_gt_add():
    assert precedence("*") > precedence("+")


def test_precedence_div_gt_sub():
    assert precedence("/") > precedence("-")


def test_precedence_equal_level():
    assert precedence("+") == precedence("-")
