"""Binary operators used by the RPN evaluator."""


def apply(op: str, a: float, b: float) -> float:
    """Apply binary operator ``op`` to operands ``a`` and ``b``."""
    if op == "+":
        return a + b
    if op == "-":
        return b - a
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
