"""Repo spec: ``rpncalc`` — a real RPN (reverse-polish-notation) calculator.

A multi-module package: a ``tokenizer`` (``tokenize`` / ``is_number`` /
``parse_number``), an ``operators`` module (``apply`` / ``safe_divide`` /
``precedence``), an ``evaluator`` (``evaluate`` / ``format_number``) that builds
on the tokenizer and operator modules, and a public ``__init__`` that re-exports
the API. Bugs span modules (e.g. a broken tokenizer that breaks the evaluator,
an evaluator that pops operands in the wrong order, or ``__init__`` wiring the
wrong function) and range from one-line type/logic slips to multi-line
algorithmic and cross-file integration errors.
"""

REPO = "rpncalc"

FILES = {
    "rpncalc/__init__.py": '''"""A small RPN (reverse-polish-notation) calculator.

Public API:
- evaluation: ``evaluate`` / ``format_number``
- operators: ``apply`` / ``safe_divide`` / ``precedence``
- tokenization: ``tokenize`` / ``is_number`` / ``parse_number``
"""

from rpncalc.evaluator import evaluate, format_number
from rpncalc.operators import apply, precedence, safe_divide
from rpncalc.tokenizer import is_number, parse_number, tokenize

__all__ = [
    "evaluate",
    "format_number",
    "apply",
    "safe_divide",
    "precedence",
    "tokenize",
    "is_number",
    "parse_number",
]
''',
    "rpncalc/tokenizer.py": '''"""Tokenization helpers for the RPN calculator."""


def is_number(token: str) -> bool:
    """Return True if ``token`` represents a number (int or float)."""
    try:
        float(token)
        return True
    except ValueError:
        return False


def parse_number(token: str) -> float:
    """Parse ``token`` into a float."""
    return float(token)


def tokenize(expression: str) -> list[str]:
    """Split ``expression`` into whitespace-delimited tokens."""
    return expression.split()
''',
    "rpncalc/operators.py": '''"""Binary operators used by the RPN evaluator."""


def apply(op: str, a: float, b: float) -> float:
    """Apply binary operator ``op`` to operands ``a`` and ``b``."""
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        return safe_divide(a, b)
    raise ValueError(f"unknown operator: {op}")


def safe_divide(a: float, b: float) -> float:
    """Divide ``a`` by ``b``, raising ``ZeroDivisionError`` when ``b`` is zero."""
    if b == 0:
        raise ZeroDivisionError("division by zero")
    return a / b


def precedence(op: str) -> int:
    """Return the precedence of ``op`` (higher binds tighter)."""
    return {"+": 1, "-": 1, "*": 2, "/": 2}.get(op, 0)
''',
    "rpncalc/evaluator.py": '''"""RPN expression evaluation."""

from rpncalc.operators import apply
from rpncalc.tokenizer import is_number, parse_number, tokenize


def format_number(value: float) -> str:
    """Format ``value`` as a compact decimal string.

    Whole numbers are shown without a trailing ``.0`` (``3.0`` -> ``"3"``); other
    values keep up to 10 significant decimal places.
    """
    if value == int(value):
        return str(int(value))
    return f"{value:.10g}"


def evaluate(expression: str) -> float:
    """Evaluate a whitespace-separated RPN ``expression`` and return a float."""
    stack = []
    for token in tokenize(expression):
        if is_number(token):
            stack.append(parse_number(token))
        else:
            if len(stack) < 2:
                raise ValueError("not enough operands")
            b = stack.pop()
            a = stack.pop()
            stack.append(apply(token, a, b))
    if len(stack) != 1:
        raise ValueError("invalid expression")
    return stack[0]
''',
}

TESTS = {
    "tests/test_tokenizer.py": '''from rpncalc.tokenizer import is_number, parse_number, tokenize


def test_tokenize_basic():
    assert tokenize("3 4 +") == ["3", "4", "+"]


def test_tokenize_single():
    assert tokenize("42") == ["42"]


def test_tokenize_empty():
    assert tokenize("") == []


def test_tokenize_extra_whitespace():
    assert tokenize("  3   4   +  ") == ["3", "4", "+"]


def test_tokenize_whitespace_mixed():
    assert tokenize("3\\t4\\n+") == ["3", "4", "+"]


def test_is_number_int():
    assert is_number("42") is True


def test_is_number_float():
    assert is_number("3.5") is True


def test_is_number_negative():
    assert is_number("-7") is True


def test_is_number_operator():
    assert is_number("+") is False


def test_is_number_non_numeric():
    assert is_number("abc") is False


def test_parse_number_int():
    assert parse_number("42") == 42


def test_parse_number_float():
    assert parse_number("3.5") == 3.5


def test_parse_number_negative():
    assert parse_number("-7") == -7
''',
    "tests/test_operators.py": '''import pytest

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
''',
    "tests/test_evaluator.py": '''import pytest

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
''',
    "tests/test_api.py": '''import rpncalc


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
''',
}

TASKS = [
    {
        "id": "rpncalc-01",
        "instruction": (
            "Fix `is_number` in `rpncalc/tokenizer.py` so it recognizes negative numbers and "
            "decimals as numbers. It currently only accepts digit-only strings, so tokens like "
            "`-7` or `3.5` are treated as operators and valid expressions are rejected."
        ),
        "difficulty": "easy",
        "category": "tokenization",
        "lines": 1,
        "bug": [
            (
                "rpncalc/tokenizer.py",
                (
                    "    try:\n"
                    "        float(token)\n"
                    "        return True\n"
                    "    except ValueError:\n"
                    "        return False"
                ),
                "    return token.isdigit()",
            )
        ],
        "fail_to_pass": [
            "tests/test_tokenizer.py::test_is_number_negative",
            "tests/test_tokenizer.py::test_is_number_float",
        ],
        "pass_to_pass": [
            "tests/test_tokenizer.py::test_is_number_int",
            "tests/test_tokenizer.py::test_is_number_operator",
            "tests/test_tokenizer.py::test_is_number_non_numeric",
        ],
    },
    {
        "id": "rpncalc-02",
        "instruction": (
            "Fix `safe_divide` in `rpncalc/operators.py` so division by zero raises "
            "`ZeroDivisionError` instead of silently returning 0. The current code swallows the "
            "error and returns 0, hiding the mistake from callers."
        ),
        "difficulty": "easy",
        "category": "operators",
        "lines": 2,
        "bug": [
            (
                "rpncalc/operators.py",
                (
                    "    if b == 0:\n"
                    "        raise ZeroDivisionError(\"division by zero\")\n"
                    "    return a / b"
                ),
                (
                    "    if b == 0:\n"
                    "        return 0\n"
                    "    return a / b"
                ),
            )
        ],
        "fail_to_pass": [
            "tests/test_operators.py::test_safe_divide_zero",
            "tests/test_evaluator.py::test_evaluate_division_by_zero",
        ],
        "pass_to_pass": [
            "tests/test_operators.py::test_safe_divide_ok",
            "tests/test_evaluator.py::test_evaluate_division",
        ],
    },
    {
        "id": "rpncalc-03",
        "instruction": (
            "Fix the `-` operator in `apply` (in `rpncalc/operators.py`) so it computes "
            "`a - b` and not `b - a`. Subtraction is not commutative, so the operand order "
            "matters and expressions like `10 4 -` currently produce the wrong sign."
        ),
        "difficulty": "easy",
        "category": "algorithm",
        "lines": 1,
        "bug": [
            (
                "rpncalc/operators.py",
                (
                    '    if op == "-":\n'
                    "        return a - b"
                ),
                (
                    '    if op == "-":\n'
                    "        return b - a"
                ),
            )
        ],
        "fail_to_pass": [
            "tests/test_operators.py::test_apply_sub",
            "tests/test_operators.py::test_apply_sub_negative_result",
        ],
        "pass_to_pass": [
            "tests/test_operators.py::test_apply_add",
            "tests/test_operators.py::test_apply_mul",
            "tests/test_operators.py::test_apply_div",
        ],
    },
    {
        "id": "rpncalc-04",
        "instruction": (
            "Fix `format_number` in `rpncalc/evaluator.py` so fractional values keep their "
            "decimals. The current code formats every value with two fixed decimal places, so "
            "`2.5` is rendered as `2.50` and other precisions are lost."
        ),
        "difficulty": "easy",
        "category": "formatting",
        "lines": 1,
        "bug": [
            (
                "rpncalc/evaluator.py",
                '    return f"{value:.10g}"',
                '    return f"{value:.2f}"',
            )
        ],
        "fail_to_pass": [
            "tests/test_evaluator.py::test_format_number_float",
            "tests/test_evaluator.py::test_format_number_negative_float",
        ],
        "pass_to_pass": [
            "tests/test_evaluator.py::test_format_number_integer",
            "tests/test_evaluator.py::test_format_number_negative_int",
        ],
    },
    {
        "id": "rpncalc-05",
        "instruction": (
            "Fix `evaluate` in `rpncalc/evaluator.py` so it applies binary operators with the "
            "operands in the correct order. The stack pops the two operands and hands them to "
            "`apply` swapped, which breaks non-commutative operators like `-` and `/`."
        ),
        "difficulty": "medium",
        "category": "algorithm",
        "lines": 1,
        "bug": [
            (
                "rpncalc/evaluator.py",
                (
                    "            b = stack.pop()\n"
                    "            a = stack.pop()\n"
                    "            stack.append(apply(token, a, b))"
                ),
                (
                    "            b = stack.pop()\n"
                    "            a = stack.pop()\n"
                    "            stack.append(apply(token, b, a))"
                ),
            )
        ],
        "fail_to_pass": [
            "tests/test_evaluator.py::test_evaluate_subtraction_order",
            "tests/test_evaluator.py::test_evaluate_division",
        ],
        "pass_to_pass": [
            "tests/test_evaluator.py::test_evaluate_addition",
            "tests/test_evaluator.py::test_evaluate_multiplication",
            "tests/test_tokenizer.py::test_tokenize_basic",
        ],
    },
    {
        "id": "rpncalc-06",
        "instruction": (
            "Fix `apply` in `rpncalc/operators.py` so the `*` operator is actually supported. "
            "The `*` case is missing, so multiplying two operands raises "
            "`ValueError: unknown operator` instead of returning the product."
        ),
        "difficulty": "medium",
        "category": "algorithm",
        "lines": 2,
        "bug": [
            (
                "rpncalc/operators.py",
                (
                    '    if op == "*":\n'
                    "        return a * b\n"
                    '    if op == "/":\n'
                    "        return safe_divide(a, b)"
                ),
                (
                    '    if op == "/":\n'
                    "        return safe_divide(a, b)"
                ),
            )
        ],
        "fail_to_pass": [
            "tests/test_operators.py::test_apply_mul",
            "tests/test_evaluator.py::test_evaluate_multiplication",
        ],
        "pass_to_pass": [
            "tests/test_operators.py::test_apply_add",
            "tests/test_operators.py::test_apply_div",
            "tests/test_evaluator.py::test_evaluate_addition",
        ],
    },
    {
        "id": "rpncalc-07",
        "instruction": (
            "Fix `precedence` in `rpncalc/operators.py` so `*` and `/` bind tighter than `+` "
            "and `-`. The precedence table is inverted, ranking addition and subtraction above "
            "multiplication and division."
        ),
        "difficulty": "medium",
        "category": "algorithm",
        "lines": 1,
        "bug": [
            (
                "rpncalc/operators.py",
                '    return {"+": 1, "-": 1, "*": 2, "/": 2}.get(op, 0)',
                '    return {"+": 2, "-": 2, "*": 1, "/": 1}.get(op, 0)',
            )
        ],
        "fail_to_pass": [
            "tests/test_operators.py::test_precedence_mul_gt_add",
            "tests/test_operators.py::test_precedence_div_gt_sub",
        ],
        "pass_to_pass": [
            "tests/test_operators.py::test_precedence_equal_level",
        ],
    },
    {
        "id": "rpncalc-08",
        "instruction": (
            "Fix `tokenize` in `rpncalc/tokenizer.py` so it splits on any whitespace, not just "
            "single spaces. The current code splits on a single space character, so runs of "
            "spaces, tabs, or newlines leave empty tokens or fail to split."
        ),
        "difficulty": "medium",
        "category": "tokenization",
        "lines": 1,
        "bug": [
            (
                "rpncalc/tokenizer.py",
                "    return expression.split()",
                '    return expression.split(" ")',
            )
        ],
        "fail_to_pass": [
            "tests/test_tokenizer.py::test_tokenize_empty",
            "tests/test_tokenizer.py::test_tokenize_extra_whitespace",
            "tests/test_tokenizer.py::test_tokenize_whitespace_mixed",
        ],
        "pass_to_pass": [
            "tests/test_tokenizer.py::test_tokenize_basic",
            "tests/test_tokenizer.py::test_tokenize_single",
        ],
    },
    {
        "id": "rpncalc-09",
        "instruction": (
            "Fix `parse_number` in `rpncalc/tokenizer.py` so it returns a numeric value instead "
            "of the raw string. It currently returns the token unchanged, so parsed numbers are "
            "strings and arithmetic breaks downstream."
        ),
        "difficulty": "medium",
        "category": "tokenization",
        "lines": 1,
        "bug": [
            (
                "rpncalc/tokenizer.py",
                "    return float(token)",
                "    return token",
            )
        ],
        "fail_to_pass": [
            "tests/test_tokenizer.py::test_parse_number_int",
            "tests/test_tokenizer.py::test_parse_number_float",
            "tests/test_tokenizer.py::test_parse_number_negative",
        ],
        "pass_to_pass": [
            "tests/test_tokenizer.py::test_tokenize_basic",
            "tests/test_tokenizer.py::test_is_number_int",
            "tests/test_tokenizer.py::test_is_number_operator",
        ],
    },
    {
        "id": "rpncalc-10",
        "instruction": (
            "Fix `evaluate` in `rpncalc/evaluator.py` so it reports an error when there are not "
            "enough operands for an operator. The operand-count check is missing, so an "
            "expression like `3 +` crashes with an `IndexError` instead of a clear `ValueError`."
        ),
        "difficulty": "hard",
        "category": "boundary",
        "lines": 2,
        "bug": [
            (
                "rpncalc/evaluator.py",
                (
                    "            if len(stack) < 2:\n"
                    '                raise ValueError("not enough operands")\n'
                    "            b = stack.pop()"
                ),
                "            b = stack.pop()",
            )
        ],
        "fail_to_pass": [
            "tests/test_evaluator.py::test_evaluate_too_few_operands",
            "tests/test_evaluator.py::test_evaluate_only_operator",
        ],
        "pass_to_pass": [
            "tests/test_evaluator.py::test_evaluate_empty_expression",
            "tests/test_evaluator.py::test_evaluate_leftover_operands",
            "tests/test_evaluator.py::test_evaluate_single_operand",
        ],
    },
    {
        "id": "rpncalc-11",
        "instruction": (
            "Fix the package's public API in `rpncalc/__init__.py` so `rpncalc.evaluate` "
            "actually evaluates expressions. The `__init__` module aliases `evaluate` to "
            "`format_number`, so calling `rpncalc.evaluate` formats the input string instead of "
            "evaluating it."
        ),
        "difficulty": "hard",
        "category": "api",
        "lines": 1,
        "bug": [
            (
                "rpncalc/__init__.py",
                "from rpncalc.evaluator import evaluate, format_number",
                "from rpncalc.evaluator import format_number, format_number as evaluate",
            )
        ],
        "fail_to_pass": [
            "tests/test_api.py::test_api_evaluate",
            "tests/test_api.py::test_api_evaluate_float",
        ],
        "pass_to_pass": [
            "tests/test_api.py::test_api_tokenize",
            "tests/test_api.py::test_api_apply",
            "tests/test_api.py::test_api_all_public_names_present",
        ],
    },
    {
        "id": "rpncalc-12",
        "instruction": (
            "Fix the calculator so fractional results are preserved rather than truncated to "
            "integers. Both the `/` operator in `rpncalc/operators.py` and `format_number` in "
            "`rpncalc/evaluator.py` drop the fractional part, so `5 2 /` yields `2` and "
            "non-integer results are mis-reported."
        ),
        "difficulty": "hard",
        "category": "integration",
        "lines": 2,
        "bug": [
            (
                "rpncalc/operators.py",
                (
                    '    if op == "/":\n'
                    "        return safe_divide(a, b)"
                ),
                (
                    '    if op == "/":\n'
                    "        return a // b"
                ),
            ),
            (
                "rpncalc/evaluator.py",
                (
                    "    if value == int(value):\n"
                    "        return str(int(value))\n"
                    '    return f"{value:.10g}"'
                ),
                "    return str(int(value))",
            ),
        ],
        "fail_to_pass": [
            "tests/test_operators.py::test_apply_div_float",
            "tests/test_evaluator.py::test_evaluate_float_result",
            "tests/test_evaluator.py::test_format_number_float",
            "tests/test_evaluator.py::test_format_number_negative_float",
        ],
        "pass_to_pass": [
            "tests/test_operators.py::test_apply_div",
            "tests/test_evaluator.py::test_evaluate_division",
            "tests/test_evaluator.py::test_format_number_integer",
            "tests/test_evaluator.py::test_format_number_negative_int",
        ],
    },
]
