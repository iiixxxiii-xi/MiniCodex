import pytest

import rpncalc


def test_is_number():
    assert rpncalc.is_number("3") is True
    assert rpncalc.is_number("3.5") is True
    assert rpncalc.is_number("-2") is True
    assert rpncalc.is_number("+") is False


def test_parse_number():
    assert rpncalc.parse_number("3") == 3
    assert rpncalc.parse_number("3.5") == 3.5


def test_apply():
    assert rpncalc.apply("+", 2, 3) == 5
    assert rpncalc.apply("/", 7, 2) == 3.5
    assert rpncalc.apply("*", 3, 4) == 12


def test_safe_divide():
    assert rpncalc.safe_divide(6, 3) == 2.0
    with pytest.raises(ZeroDivisionError):
        rpncalc.safe_divide(1, 0)


def test_precedence():
    assert rpncalc.precedence("*") > rpncalc.precedence("+")
    assert rpncalc.precedence("/") == rpncalc.precedence("*")


def test_tokenize():
    assert rpncalc.tokenize("12 3 +") == ["12", "3", "+"]


def test_evaluate():
    assert rpncalc.evaluate(["5", "3", "-"]) == 2
    assert rpncalc.evaluate(["2", "3", "+"]) == 5


def test_format_number():
    assert rpncalc.format_number(3) == "3"
    assert rpncalc.format_number(3.5) == "3.5"
