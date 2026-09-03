"""RPN expression evaluation."""

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
            b = stack.pop()
            a = stack.pop()
            stack.append(apply(token, a, b))
    if len(stack) != 1:
        raise ValueError("invalid expression")
    return stack[0]
