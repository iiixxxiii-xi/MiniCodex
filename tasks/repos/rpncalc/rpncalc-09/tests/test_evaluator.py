import pytest

from rpncalc.evaluator import evaluate, format_number


def test_evaluate_addition():
    assert evaluate("3 4 +") == 7


def test_evaluate_subtraction_order():
    assert evaluate("10 4 -") == 6


def test_evaluate_multiplication():
    assert evaluate("3 4 *") == 12


def test_evaluate_division():
    assert evaluate("12 4 /") == 3


def test_evaluate_complex():
    assert evaluate("5 1 2 + 4 * + 3 -") == 14


def test_evaluate_negative_numbers():
    assert evaluate("-3 -4 +") == -7


def test_evaluate_float_result():
    assert evaluate("5 2 /") == 2.5


def test_evaluate_single_operand():
    assert evaluate("42") == 42


def test_evaluate_division_by_zero():
    with pytest.raises(ZeroDivisionError):
        evaluate("1 0 /")


def test_evaluate_empty_expression():
    with pytest.raises(ValueError):
        evaluate("")


def test_evaluate_too_few_operands():
    with pytest.raises(ValueError):
        evaluate("3 +")


def test_evaluate_only_operator():
    with pytest.raises(ValueError):
        evaluate("+")


def test_evaluate_leftover_operands():
    with pytest.raises(ValueError):
        evaluate("3 4 5 +")


def test_evaluate_leftover_operands_two():
    with pytest.raises(ValueError):
        evaluate("1 2 3")


def test_format_number_integer():
    assert format_number(3.0) == "3"


def test_format_number_float():
    assert format_number(2.5) == "2.5"


def test_format_number_negative_int():
    assert format_number(-7.0) == "-7"


def test_format_number_negative_float():
    assert format_number(-2.5) == "-2.5"
