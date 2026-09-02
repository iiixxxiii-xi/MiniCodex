"""Small reverse-polish-notation calculator (intentionally buggy for eval tasks)."""


def is_number(token):
    """Return True if ``token`` can be parsed as a number."""
    try:
        float(token)
        return True
    except ValueError:
        return False


def parse_number(token):
    """Parse ``token`` into an int or float."""
    return float(token) if "." in token else int(token)


def apply(op, a, b):
    """Apply binary operator ``op`` to ``a`` and ``b``."""
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        return a / b
    raise ValueError(f"unknown operator: {op}")


def safe_divide(a, b):
    """Divide ``a`` by ``b``, raising ZeroDivisionError on division by zero."""
    if b == 0:
        raise ZeroDivisionError("division by zero")
    return a / b


def precedence(op):
    """Return the precedence of operator ``op`` (higher binds tighter)."""
    return {"+": 1, "-": 1, "*": 2, "/": 2}[op]


def tokenize(expr):
    """Split an RPN expression string into tokens."""
    return expr.split()


def evaluate(tokens):
    """Evaluate an RPN expression given as a list of tokens."""
    stack = []
    for token in tokens:
        if token in ("+", "-", "*", "/"):
            b = stack.pop()
            a = stack.pop()
            stack.append(apply(token, a, b))
        else:
            stack.append(parse_number(token))
    return stack[0]


def format_number(value):
    """Format a number for display (drop a trailing '.0')."""
    return str(int(value))
