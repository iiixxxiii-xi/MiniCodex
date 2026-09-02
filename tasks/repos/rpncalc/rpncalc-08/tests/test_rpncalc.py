import pytest

import rpncalc


def test_is_number_float():
    assert rpncalc.is_number("3.5") is True


def test_is_number_negative():
    assert rpncalc.is_number("-2") is True


def test_is_number_int():
    assert rpncalc.is_number("3") is True


def test_is_number_operator():
    assert rpncalc.is_number("+") is False


def test_parse_number_float():
    assert rpncalc.parse_number("3.5") == 3.5


def test_parse_number_negative_float():
    assert rpncalc.parse_number("-2.5") == -2.5


def test_parse_number_int():
    assert rpncalc.parse_number("3") == 3


def test_apply_divide_float():
    assert rpncalc.apply("/", 7, 2) == 3.5


def test_apply_divide_fraction():
    assert rpncalc.apply("/", 1, 4) == 0.25


def test_apply_add():
    assert rpncalc.apply("+", 2, 3) == 5


def test_safe_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        rpncalc.safe_divide(1, 0)


def test_safe_divide_zero_dividend():
    with pytest.raises(ZeroDivisionError):
        rpncalc.safe_divide(0, 0)


def test_safe_divide_basic():
    assert rpncalc.safe_divide(6, 3) == 2.0


def test_precedence_mul_tighter():
    assert rpncalc.precedence("*") > rpncalc.precedence("+")


def test_precedence_div_tighter():
    assert rpncalc.precedence("/") > rpncalc.precedence("-")


def test_precedence_div_equals_mul():
    assert rpncalc.precedence("/") == rpncalc.precedence("*")


def test_tokenize_multi():
    assert rpncalc.tokenize("12 3 +") == ["12", "3", "+"]


def test_tokenize_multi_two():
    assert rpncalc.tokenize("5 10 -") == ["5", "10", "-"]


def test_tokenize_single():
    assert rpncalc.tokenize("7") == ["7"]


def test_evaluate_subtraction():
    assert rpncalc.evaluate(["5", "3", "-"]) == 2


def test_evaluate_division():
    assert rpncalc.evaluate(["8", "2", "/"]) == 4.0


def test_evaluate_addition():
    assert rpncalc.evaluate(["2", "3", "+"]) == 5


def test_format_number_float():
    assert rpncalc.format_number(3.5) == "3.5"


def test_format_number_negative_float():
    assert rpncalc.format_number(-2.5) == "-2.5"


def test_format_number_int():
    assert rpncalc.format_number(3) == "3"
