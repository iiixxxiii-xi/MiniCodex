"""A small RPN (reverse-polish-notation) calculator.

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
