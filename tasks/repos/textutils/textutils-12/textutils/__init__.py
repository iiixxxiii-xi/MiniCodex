"""A small, dependency-free string-utilities library.

Public API:
- word ops: ``reverse_words`` / ``capitalize_words`` / ``count_vowels``
- case/slug: ``slugify`` / ``camel_to_snake``
- comparison: ``is_palindrome`` / ``common_prefix``
- wrapping/search: ``wrap`` / ``count_occurrences``
"""

from textutils.case import camel_to_snake, slugify
from textutils.compare import common_prefix, is_palindrome
from textutils.words import capitalize_words, count_vowels, reverse_words
from textutils.wrapping import count_occurrences

__all__ = [
    "reverse_words",
    "capitalize_words",
    "count_vowels",
    "slugify",
    "camel_to_snake",
    "is_palindrome",
    "common_prefix",
    "wrap",
    "count_occurrences",
]
