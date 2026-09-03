import rpncalc


def test_api_evaluate():
    assert rpncalc.evaluate("3 4 +") == 7


def test_api_evaluate_float():
    assert rpncalc.evaluate("5 2 /") == 2.5


def test_api_tokenize():
    assert rpncalc.tokenize("3 4 +") == ["3", "4", "+"]


def test_api_apply():
    assert rpncalc.apply("*", 3, 4) == 12


def test_api_safe_divide():
    assert rpncalc.safe_divide(12, 4) == 3


def test_api_precedence():
    assert rpncalc.precedence("*") > rpncalc.precedence("+")


def test_api_all_public_names_present():
    for name in [
        "evaluate",
        "format_number",
        "apply",
        "safe_divide",
        "precedence",
        "tokenize",
        "is_number",
        "parse_number",
    ]:
        assert hasattr(rpncalc, name), f"missing {name}"
