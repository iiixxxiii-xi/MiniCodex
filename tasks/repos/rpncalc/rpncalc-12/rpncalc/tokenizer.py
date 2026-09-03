"""Tokenization helpers for the RPN calculator."""


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
