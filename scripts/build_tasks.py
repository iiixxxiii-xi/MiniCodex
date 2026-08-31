"""Build the minicodex repo-level task set and verify every task.

This script is the single source of truth for the hand-crafted repo-level tasks.
For each repo it materialises:

  tasks/repos/<repo>/<repo>.py          # the intentionally buggy module
  tasks/repos/<repo>/conftest.py        # sys.path setup for pytest
  tasks/repos/<repo>/tests/test_<repo>.py

and for each task a flat JSON file ``tasks/<id>.json`` whose ``gold_patch`` is a
real unified diff (generated with difflib from the buggy source vs the source
with exactly that one bug fixed) and whose ``test_command`` runs the single
pytest that fails on the bug and passes on the fix.

After building it verifies every task independently:
  1. buggy code  -> test exits non-zero (FAIL)
  2. apply gold_patch -> test exits zero (PASS)

Run:  uv run python scripts/build_tasks.py
"""

from __future__ import annotations

import difflib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
REPOS_DIR = TASKS_DIR / "repos"

CONFTEST = '''import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
'''


def apply_fix(source: str, old: str, new: str) -> str:
    """Replace the single unique ``old`` substring with ``new`` in ``source``."""
    n = source.count(old)
    if n != 1:
        raise ValueError(f"fix anchor not unique (count={n}): {old!r}")
    return source.replace(old, new, 1)


def make_patch(buggy: str, fixed: str, filename: str) -> str:
    """Return a unified diff (git apply-able) turning ``buggy`` into ``fixed``."""
    diff = list(
        difflib.unified_diff(
            buggy.splitlines(keepends=True),
            fixed.splitlines(keepends=True),
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        )
    )
    if not diff:
        return ""
    return f"diff --git a/{filename} b/{filename}\n" + "".join(diff)


# --------------------------------------------------------------------------- #
# textutils
# --------------------------------------------------------------------------- #

TEXTUTILS_MODULE = '''"""Small string utility library (intentionally buggy for eval tasks)."""


def reverse_words(s):
    """Return the words of ``s`` in reverse order."""
    words = s.split()
    result = []
    for i in range(len(words) - 1, 0, -1):
        result.append(words[i])
    return " ".join(result)


def capitalize_words(s):
    """Capitalize the first letter of each word, preserving the rest."""
    return " ".join(w.capitalize() for w in s.split())


def count_vowels(s):
    """Count the vowels (a, e, i, o, u) in ``s``."""
    return sum(1 for c in s if c in "aeiou")


def truncate(s, n):
    """Truncate ``s`` to ``n`` characters, appending '...' when truncated."""
    return s[:n] + "..."


def slugify(s):
    """Lowercase ``s`` and replace runs of whitespace with a single dash."""
    return s.lower().replace(" ", "-")


def camel_to_snake(s):
    """Convert ``CamelCase`` to ``snake_case``."""
    result = []
    for c in s:
        if c.isupper():
            result.append("_")
        result.append(c.lower())
    return "".join(result)


def is_palindrome(s):
    """Return True if ``s`` is a palindrome ignoring case and spaces."""
    return s == s[::-1]


def common_prefix(a, b):
    """Return the longest common prefix of ``a`` and ``b``."""
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    return a[:i - 1]


def wrap(text, width):
    """Wrap ``text`` into lines of at most ``width`` characters."""
    return "\\n".join(text[i:i + width - 1] for i in range(0, len(text), width))


def count_occurrences(text, sub):
    """Count non-overlapping occurrences of ``sub`` in ``text``."""
    count = 0
    i = 0
    while i < len(text):
        if text.startswith(sub, i):
            count += 1
        i += 1
    return count
'''

TEXTUTILS_TESTS = '''import textutils


def test_reverse_words():
    assert textutils.reverse_words("hello world") == "world hello"
    assert textutils.reverse_words("a b c") == "c b a"


def test_capitalize_words():
    assert textutils.capitalize_words("hello world") == "Hello World"
    assert textutils.capitalize_words("hello WORLD") == "Hello WORLD"


def test_count_vowels():
    assert textutils.count_vowels("Hello wOrld") == 3
    assert textutils.count_vowels("aeiou") == 5
    assert textutils.count_vowels("AEIOU") == 5


def test_truncate():
    assert textutils.truncate("hello", 10) == "hello"
    assert textutils.truncate("hello world", 5) == "hello..."


def test_slugify():
    assert textutils.slugify("Hello World") == "hello-world"
    assert textutils.slugify("  Hello   World  ") == "hello-world"


def test_camel_to_snake():
    assert textutils.camel_to_snake("HelloWorld") == "hello_world"
    assert textutils.camel_to_snake("hello") == "hello"


def test_is_palindrome():
    assert textutils.is_palindrome("racecar") is True
    assert textutils.is_palindrome("A man a plan a canal Panama") is True
    assert textutils.is_palindrome("hello") is False


def test_common_prefix():
    assert textutils.common_prefix("abcdef", "abcxyz") == "abc"
    assert textutils.common_prefix("abc", "def") == ""


def test_wrap():
    assert textutils.wrap("abcdef", 3) == "abc\\ndef"
    assert textutils.wrap("hello", 10) == "hello"


def test_count_occurrences():
    assert textutils.count_occurrences("aaaa", "aa") == 2
    assert textutils.count_occurrences("hello", "l") == 2
'''

TEXTUTILS_TASKS = [
    {
        "id": "textutils-01",
        "test": "test_reverse_words",
        "instruction": "Fix `reverse_words` so it returns the words in reverse order. "
        "It currently drops the first word because of an off-by-one in the loop range.",
        "difficulty": "medium",
        "category": "string",
        "lines": 1,
        "fix": ("for i in range(len(words) - 1, 0, -1):", "for i in range(len(words) - 1, -1, -1):"),
    },
    {
        "id": "textutils-02",
        "test": "test_capitalize_words",
        "instruction": "Fix `capitalize_words` so it capitalizes the first letter of each word "
        "while preserving the remaining characters. `str.capitalize()` lowercases the rest of the word.",
        "difficulty": "easy",
        "category": "string",
        "lines": 1,
        "fix": (
            'return " ".join(w.capitalize() for w in s.split())',
            'return " ".join((w[:1].upper() + w[1:] if w else w) for w in s.split())',
        ),
    },
    {
        "id": "textutils-03",
        "test": "test_count_vowels",
        "instruction": "Fix `count_vowels` so it counts uppercase vowels as well as lowercase ones.",
        "difficulty": "easy",
        "category": "string",
        "lines": 1,
        "fix": (
            'return sum(1 for c in s if c in "aeiou")',
            'return sum(1 for c in s if c.lower() in "aeiou")',
        ),
    },
    {
        "id": "textutils-04",
        "test": "test_truncate",
        "instruction": "Fix `truncate` so it only appends '...' when the string is actually longer "
        "than n. It currently appends the ellipsis unconditionally.",
        "difficulty": "easy",
        "category": "string",
        "lines": 1,
        "fix": (
            'return s[:n] + "..."',
            'return s if len(s) <= n else s[:n] + "..."',
        ),
    },
    {
        "id": "textutils-05",
        "test": "test_slugify",
        "instruction": "Fix `slugify` so consecutive spaces collapse into a single dash and "
        "leading/trailing whitespace is removed.",
        "difficulty": "easy",
        "category": "string",
        "lines": 1,
        "fix": (
            'return s.lower().replace(" ", "-")',
            'return "-".join(s.lower().split())',
        ),
    },
    {
        "id": "textutils-06",
        "test": "test_camel_to_snake",
        "instruction": "Fix `camel_to_snake` so the first uppercase letter does not produce a "
        "leading underscore in the result.",
        "difficulty": "medium",
        "category": "string",
        "lines": 2,
        "fix": (
            "    for c in s:\n        if c.isupper():\n            result.append(\"_\")",
            "    for i, c in enumerate(s):\n        if c.isupper() and i > 0:\n            result.append(\"_\")",
        ),
    },
    {
        "id": "textutils-07",
        "test": "test_is_palindrome",
        "instruction": "Fix `is_palindrome` so it ignores case and spaces when checking whether "
        "a string is a palindrome.",
        "difficulty": "medium",
        "category": "string",
        "lines": 2,
        "fix": (
            "    return s == s[::-1]",
            '    s = "".join(s.lower().split())\n    return s == s[::-1]',
        ),
    },
    {
        "id": "textutils-08",
        "test": "test_common_prefix",
        "instruction": "Fix `common_prefix` so it returns the full common prefix without dropping "
        "the last matching character (off-by-one in the return slice).",
        "difficulty": "medium",
        "category": "string",
        "lines": 1,
        "fix": ("    return a[:i - 1]", "    return a[:i]"),
    },
    {
        "id": "textutils-09",
        "test": "test_wrap",
        "instruction": "Fix `wrap` so each line contains the full `width` characters. It currently "
        "drops the last character of every line.",
        "difficulty": "easy",
        "category": "string",
        "lines": 1,
        "fix": ("text[i:i + width - 1]", "text[i:i + width]"),
    },
    {
        "id": "textutils-10",
        "test": "test_count_occurrences",
        "instruction": "Fix `count_occurrences` to count only non-overlapping occurrences. It "
        "currently advances one character at a time even after a match.",
        "difficulty": "medium",
        "category": "string",
        "lines": 4,
        "fix": (
            "        if text.startswith(sub, i):\n            count += 1\n        i += 1",
            "        if text.startswith(sub, i):\n            count += 1\n            i += len(sub)\n        else:\n            i += 1",
        ),
    },
]

# --------------------------------------------------------------------------- #
# numstats
# --------------------------------------------------------------------------- #

NUMSTATS_MODULE = '''"""Small numeric/statistics library (intentionally buggy for eval tasks)."""


def mean(values):
    """Return the arithmetic mean of ``values``."""
    return sum(values) / len(values)


def median(values):
    """Return the median of ``values``."""
    s = sorted(values)
    n = len(s)
    return s[n // 2]


def mode(values):
    """Return the most frequent value in ``values``."""
    return max(values.count(v) for v in set(values))


def variance(values):
    """Return the sample variance of ``values``."""
    m = sum(values) / len(values)
    return sum((x - m) ** 2 for x in values) / len(values)


def percentile(values, p):
    """Return the ``p``-th percentile (0-100) of ``values``."""
    s = sorted(values)
    idx = int(len(s) * p / 100)
    return s[idx]


def moving_average(values, window):
    """Return the moving average of ``values`` over ``window``."""
    return [sum(values[i:i + window]) / window for i in range(len(values))]


def clamp(value, lo, hi):
    """Clamp ``value`` to the inclusive range [lo, hi]."""
    if value < lo:
        return hi
    if value > hi:
        return lo
    return value


def fibonacci(n):
    """Return the n-th Fibonacci number (fib(0)=0, fib(1)=1)."""
    if n <= 1:
        return 1
    return fibonacci(n - 1) + fibonacci(n - 2)


def is_prime(n):
    """Return True if ``n`` is prime."""
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True


def gcd(a, b):
    """Return the greatest common divisor of ``a`` and ``b``."""
    while b:
        a, b = b, a % b
    return b
'''

NUMSTATS_TESTS = '''import pytest

import numstats


def test_mean():
    assert numstats.mean([1, 2, 3, 4]) == 2.5
    with pytest.raises(ValueError):
        numstats.mean([])


def test_median():
    assert numstats.median([1, 2, 3, 4]) == 2.5
    assert numstats.median([1, 2, 3]) == 2


def test_mode():
    assert numstats.mode([1, 1, 2, 3]) == 1
    assert numstats.mode(["a", "b", "a"]) == "a"


def test_variance():
    assert abs(numstats.variance([1, 2, 3, 4]) - 5 / 3) < 1e-9


def test_percentile():
    assert numstats.percentile([1, 2, 3, 4, 5], 50) == 3
    assert numstats.percentile([1, 2, 3, 4, 5], 100) == 5


def test_moving_average():
    assert numstats.moving_average([1, 2, 3, 4, 5], 3) == [2.0, 3.0, 4.0]


def test_clamp():
    assert numstats.clamp(0, 1, 10) == 1
    assert numstats.clamp(50, 1, 10) == 10
    assert numstats.clamp(5, 1, 10) == 5


def test_fibonacci():
    assert numstats.fibonacci(0) == 0
    assert numstats.fibonacci(1) == 1
    assert numstats.fibonacci(6) == 8


def test_is_prime():
    assert numstats.is_prime(1) is False
    assert numstats.is_prime(2) is True
    assert numstats.is_prime(4) is False
    assert numstats.is_prime(17) is True


def test_gcd():
    assert numstats.gcd(48, 18) == 6
    assert numstats.gcd(0, 5) == 5
'''

NUMSTATS_TASKS = [
    {
        "id": "numstats-01",
        "test": "test_mean",
        "instruction": "Fix `mean` so it raises a `ValueError` for an empty input list instead of "
        "crashing with a division-by-zero error.",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 2,
        "fix": (
            "    return sum(values) / len(values)",
            "    if not values:\n        raise ValueError(\"mean of empty sequence\")\n    return sum(values) / len(values)",
        ),
    },
    {
        "id": "numstats-02",
        "test": "test_median",
        "instruction": "Fix `median` so it returns the average of the two middle elements for "
        "even-length inputs instead of only the upper-middle element.",
        "difficulty": "medium",
        "category": "numeric",
        "lines": 3,
        "fix": (
            "    return s[n // 2]",
            "    if n % 2 == 0:\n        return (s[n // 2 - 1] + s[n // 2]) / 2\n    return s[n // 2]",
        ),
    },
    {
        "id": "numstats-03",
        "test": "test_mode",
        "instruction": "Fix `mode` so it returns the most frequent value itself rather than the "
        "frequency count.",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 1,
        "fix": (
            "    return max(values.count(v) for v in set(values))",
            "    return max(set(values), key=values.count)",
        ),
    },
    {
        "id": "numstats-04",
        "test": "test_variance",
        "instruction": "Fix `variance` so it computes the sample variance (divide by n-1) rather "
        "than the population variance (divide by n).",
        "difficulty": "medium",
        "category": "numeric",
        "lines": 1,
        "fix": (
            "return sum((x - m) ** 2 for x in values) / len(values)",
            "return sum((x - m) ** 2 for x in values) / (len(values) - 1)",
        ),
    },
    {
        "id": "numstats-05",
        "test": "test_percentile",
        "instruction": "Fix `percentile` so p=100 does not index past the end of the sorted list.",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 1,
        "fix": (
            "    idx = int(len(s) * p / 100)\n    return s[idx]",
            "    idx = min(int(len(s) * p / 100), len(s) - 1)\n    return s[idx]",
        ),
    },
    {
        "id": "numstats-06",
        "test": "test_moving_average",
        "instruction": "Fix `moving_average` so it only produces full windows of `window` elements "
        "(the current range over-iterates and emits trailing partial windows).",
        "difficulty": "medium",
        "category": "numeric",
        "lines": 1,
        "fix": (
            "for i in range(len(values))]",
            "for i in range(len(values) - window + 1)]",
        ),
    },
    {
        "id": "numstats-07",
        "test": "test_clamp",
        "instruction": "Fix `clamp` so it returns the lower bound when the value is below the range "
        "and the upper bound when it is above (the two returns are currently swapped).",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 2,
        "fix": (
            "    if value < lo:\n        return hi\n    if value > hi:\n        return lo",
            "    if value < lo:\n        return lo\n    if value > hi:\n        return hi",
        ),
    },
    {
        "id": "numstats-08",
        "test": "test_fibonacci",
        "instruction": "Fix `fibonacci` so fib(0) returns 0 (the base case currently returns 1 for "
        "both 0 and 1).",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 1,
        "fix": (
            "    if n <= 1:\n        return 1",
            "    if n <= 1:\n        return n",
        ),
    },
    {
        "id": "numstats-09",
        "test": "test_is_prime",
        "instruction": "Fix `is_prime` so it returns False for n less than 2 (1 and 0 are not prime).",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 2,
        "fix": (
            "    for i in range(2, int(n ** 0.5) + 1):",
            "    if n < 2:\n        return False\n    for i in range(2, int(n ** 0.5) + 1):",
        ),
    },
    {
        "id": "numstats-10",
        "test": "test_gcd",
        "instruction": "Fix `gcd` so it returns the greatest common divisor (`a`) instead of always "
        "returning the remainder (`b`), which ends up as zero.",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 1,
        "fix": ("    return b", "    return a"),
    },
]

# --------------------------------------------------------------------------- #
# rpncalc
# --------------------------------------------------------------------------- #

RPNCALC_MODULE = '''"""Small reverse-polish-notation calculator (intentionally buggy for eval tasks)."""


def is_number(token):
    """Return True if ``token`` can be parsed as a number."""
    return token.isdigit()


def parse_number(token):
    """Parse ``token`` into an int or float."""
    return int(token)


def apply(op, a, b):
    """Apply binary operator ``op`` to ``a`` and ``b``."""
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        return a // b
    raise ValueError(f"unknown operator: {op}")


def safe_divide(a, b):
    """Divide ``a`` by ``b``, raising ZeroDivisionError on division by zero."""
    if b == 0:
        return 0
    return a / b


def precedence(op):
    """Return the precedence of operator ``op`` (higher binds tighter)."""
    return {"+": 1, "-": 1, "*": 1, "/": 1}[op]


def tokenize(expr):
    """Split an RPN expression string into tokens."""
    return list(expr.replace(" ", ""))


def evaluate(tokens):
    """Evaluate an RPN expression given as a list of tokens."""
    stack = []
    for token in tokens:
        if token in ("+", "-", "*", "/"):
            a = stack.pop()
            b = stack.pop()
            stack.append(apply(token, a, b))
        else:
            stack.append(parse_number(token))
    return stack[0]


def format_number(value):
    """Format a number for display (drop a trailing '.0')."""
    return str(int(value))
'''

RPNCALC_TESTS = '''import pytest

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
'''

RPNCALC_TASKS = [
    {
        "id": "rpncalc-01",
        "test": "test_is_number",
        "instruction": "Fix `is_number` so it recognises floats and negative numbers, not just "
        "all-digit strings.",
        "difficulty": "easy",
        "category": "parsing",
        "lines": 3,
        "fix": (
            "    return token.isdigit()",
            "    try:\n        float(token)\n        return True\n    except ValueError:\n        return False",
        ),
    },
    {
        "id": "rpncalc-02",
        "test": "test_parse_number",
        "instruction": "Fix `parse_number` so it parses floats (e.g. \"3.5\") instead of only "
        "integers.",
        "difficulty": "easy",
        "category": "parsing",
        "lines": 1,
        "fix": (
            "    return int(token)",
            '    return float(token) if "." in token else int(token)',
        ),
    },
    {
        "id": "rpncalc-03",
        "test": "test_apply",
        "instruction": "Fix `apply` so the division operator returns a float result instead of "
        "truncating with integer floor division.",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 1,
        "fix": ("        return a // b", "        return a / b"),
    },
    {
        "id": "rpncalc-04",
        "test": "test_safe_divide",
        "instruction": "Fix `safe_divide` so it raises `ZeroDivisionError` on division by zero "
        "instead of silently returning 0.",
        "difficulty": "easy",
        "category": "edge-case",
        "lines": 2,
        "fix": (
            "    if b == 0:\n        return 0\n    return a / b",
            "    if b == 0:\n        raise ZeroDivisionError(\"division by zero\")\n    return a / b",
        ),
    },
    {
        "id": "rpncalc-05",
        "test": "test_precedence",
        "instruction": "Fix `precedence` so multiplication and division bind tighter (higher value) "
        "than addition and subtraction.",
        "difficulty": "easy",
        "category": "parsing",
        "lines": 1,
        "fix": (
            'return {"+": 1, "-": 1, "*": 1, "/": 1}[op]',
            'return {"+": 1, "-": 1, "*": 2, "/": 2}[op]',
        ),
    },
    {
        "id": "rpncalc-06",
        "test": "test_tokenize",
        "instruction": "Fix `tokenize` so it splits on whitespace and keeps multi-character numbers "
        "intact (it currently splits every character).",
        "difficulty": "easy",
        "category": "parsing",
        "lines": 1,
        "fix": ('return list(expr.replace(" ", ""))', "return expr.split()"),
    },
    {
        "id": "rpncalc-07",
        "test": "test_evaluate",
        "instruction": "Fix `evaluate` so it pops the operands in the correct order for "
        "non-commutative operators (subtraction and division currently produce reversed results).",
        "difficulty": "medium",
        "category": "algorithm",
        "lines": 2,
        "fix": (
            "            a = stack.pop()\n            b = stack.pop()\n            stack.append(apply(token, a, b))",
            "            b = stack.pop()\n            a = stack.pop()\n            stack.append(apply(token, a, b))",
        ),
    },
    {
        "id": "rpncalc-08",
        "test": "test_format_number",
        "instruction": "Fix `format_number` so it preserves the fractional part for non-integer "
        "values instead of truncating with int().",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 1,
        "fix": (
            "    return str(int(value))",
            "    return str(int(value)) if value == int(value) else str(value)",
        ),
    },
]

# --------------------------------------------------------------------------- #
# datastore
# --------------------------------------------------------------------------- #

DATASTORE_MODULE = '''"""Small JSON/CSV data utilities (intentionally buggy for eval tasks)."""

import json


def parse_json(text):
    """Parse a JSON string into a Python object."""
    return json.loads(text)


def parse_csv(text):
    """Parse a CSV string into a list of rows (lists of fields)."""
    return [line.split(",") for line in text.splitlines()]


def filter_records(records, key, value):
    """Return records whose ``key`` equals ``value``."""
    return [r for r in records if r.get(key) != value]


def group_by(records, key):
    """Group records by the value of ``key`` (missing key -> 'unknown')."""
    groups = {}
    for r in records:
        groups.setdefault(r[key], []).append(r)
    return groups


def to_csv(rows, delimiter=","):
    """Serialize a list of rows into a CSV string using ``delimiter``."""
    return "\\n".join(",".join(map(str, row)) for row in rows)


def summarize(values):
    """Sum a list of numeric strings/values into a float."""
    total = 0
    for v in values:
        total += int(v)
    return total


def nested_get(obj, path):
    """Return the value at a dotted ``path`` (e.g. 'a.b.c') or None if missing."""
    for part in path.split("."):
        obj = obj[part]
    return obj


def dedupe(records, key):
    """Remove records with duplicate ``key`` values, keeping the first."""
    seen = set()
    out = []
    for r in records:
        if r[key] in seen:
            out.append(r)
        seen.add(r[key])
    return out
'''

DATASTORE_TESTS = '''import datastore


def test_parse_json():
    assert datastore.parse_json('{"a": 1}') == {"a": 1}
    assert datastore.parse_json("") == {}


def test_parse_csv():
    assert datastore.parse_csv("a, b\\n1, 2") == [["a", "b"], ["1", "2"]]


def test_filter_records():
    records = [{"k": 1}, {"k": 2}, {"k": 1}]
    assert datastore.filter_records(records, "k", 1) == [{"k": 1}, {"k": 1}]


def test_group_by():
    records = [{"k": "a", "v": 1}, {"v": 2}, {"k": "a", "v": 3}]
    assert datastore.group_by(records, "k") == {
        "a": [{"k": "a", "v": 1}, {"k": "a", "v": 3}],
        "unknown": [{"v": 2}],
    }


def test_to_csv():
    assert datastore.to_csv([["a", "b"], ["c", "d"]]) == "a,b\\nc,d"
    assert datastore.to_csv([["a", "b"]], delimiter=";") == "a;b"


def test_summarize():
    assert datastore.summarize(["1.5", "2.5"]) == 4.0


def test_nested_get():
    assert datastore.nested_get({"a": {"b": 1}}, "a.b") == 1
    assert datastore.nested_get({"a": {}}, "a.b.c") is None


def test_dedupe():
    records = [{"id": 1, "v": "a"}, {"id": 1, "v": "b"}, {"id": 2, "v": "c"}]
    assert datastore.dedupe(records, "id") == [{"id": 1, "v": "a"}, {"id": 2, "v": "c"}]
'''

DATASTORE_TASKS = [
    {
        "id": "datastore-01",
        "test": "test_parse_json",
        "instruction": "Fix `parse_json` so an empty string parses to an empty dict instead of "
        "raising a JSON decode error.",
        "difficulty": "easy",
        "category": "data",
        "lines": 2,
        "fix": (
            "    return json.loads(text)",
            "    if not text.strip():\n        return {}\n    return json.loads(text)",
        ),
    },
    {
        "id": "datastore-02",
        "test": "test_parse_csv",
        "instruction": "Fix `parse_csv` so each field is stripped of surrounding whitespace.",
        "difficulty": "easy",
        "category": "data",
        "lines": 1,
        "fix": (
            'return [line.split(",") for line in text.splitlines()]',
            'return [[f.strip() for f in line.split(",")] for line in text.splitlines()]',
        ),
    },
    {
        "id": "datastore-03",
        "test": "test_filter_records",
        "instruction": "Fix `filter_records` so it keeps records whose key equals the given value "
        "(the comparison operator is currently inverted).",
        "difficulty": "easy",
        "category": "data",
        "lines": 1,
        "fix": (
            "return [r for r in records if r.get(key) != value]",
            "return [r for r in records if r.get(key) == value]",
        ),
    },
    {
        "id": "datastore-04",
        "test": "test_group_by",
        "instruction": "Fix `group_by` so records missing the key are grouped under 'unknown' "
        "instead of raising a KeyError.",
        "difficulty": "medium",
        "category": "data",
        "lines": 1,
        "fix": (
            'groups.setdefault(r[key], []).append(r)',
            'groups.setdefault(r.get(key, "unknown"), []).append(r)',
        ),
    },
    {
        "id": "datastore-05",
        "test": "test_to_csv",
        "instruction": "Fix `to_csv` so it honours the `delimiter` argument instead of always "
        "joining with a comma.",
        "difficulty": "medium",
        "category": "data",
        "lines": 1,
        "fix": (
            'return "\\n".join(",".join(map(str, row)) for row in rows)',
            'return "\\n".join(delimiter.join(map(str, row)) for row in rows)',
        ),
    },
    {
        "id": "datastore-06",
        "test": "test_summarize",
        "instruction": "Fix `summarize` so it sums floats (e.g. \"1.5\") instead of coercing every "
        "value with int() and crashing on decimals.",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 1,
        "fix": ("        total += int(v)", "        total += float(v)"),
    },
    {
        "id": "datastore-07",
        "test": "test_nested_get",
        "instruction": "Fix `nested_get` so it returns None when a key in the dotted path is "
        "missing instead of raising a KeyError.",
        "difficulty": "hard",
        "category": "data",
        "lines": 7,
        "fix": (
            "    for part in path.split(\".\"):\n        obj = obj[part]\n    return obj",
            "    for part in path.split(\".\"):\n        if not isinstance(obj, dict) or part not in obj:\n            return None\n        obj = obj[part]\n    return obj",
        ),
    },
    {
        "id": "datastore-08",
        "test": "test_dedupe",
        "instruction": "Fix `dedupe` so it keeps the first occurrence of each key (it currently "
        "keeps the duplicates instead).",
        "difficulty": "medium",
        "category": "data",
        "lines": 2,
        "fix": (
            "        if r[key] in seen:\n            out.append(r)\n        seen.add(r[key])",
            "        if r[key] not in seen:\n            out.append(r)\n        seen.add(r[key])",
        ),
    },
]

# --------------------------------------------------------------------------- #
# seqops
# --------------------------------------------------------------------------- #

SEQOPS_MODULE = '''"""Small sequence-algorithm library (intentionally buggy for eval tasks)."""


def binary_search(arr, target):
    """Return the index of ``target`` in sorted ``arr``, or -1 if absent."""
    lo, hi = 0, len(arr)
    while lo < hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def merge_sorted(a, b):
    """Merge two sorted lists into one sorted list."""
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            out.append(a[i])
            i += 1
        else:
            out.append(b[j])
            j += 1
    return out


def remove_duplicates(seq):
    """Return ``seq`` with duplicates removed, preserving order."""
    return list(set(seq))


def rotate(seq, k):
    """Rotate ``seq`` to the left by ``k`` positions."""
    return seq[k:] + seq[:k]


def partition(seq, pivot):
    """Return (left, right) where left <= pivot < right."""
    left = [x for x in seq if x < pivot]
    right = [x for x in seq if x > pivot]
    return left, right


def flatten(nested):
    """Flatten a nested list of lists into a single list."""
    return [item for sublist in nested for item in sublist]


def chunk(seq, size):
    """Split ``seq`` into chunks of ``size``."""
    return [seq[i:i + size] for i in range(0, len(seq) - size, size)]


def max_subarray(nums):
    """Return the maximum subarray sum (Kadane's algorithm)."""
    best = 0
    current = 0
    for x in nums:
        current = max(x, current + x)
        best = max(best, current)
    return best
'''

SEQOPS_TESTS = '''import seqops


def test_binary_search():
    assert seqops.binary_search([1, 2, 3, 4, 5], 3) == 2
    assert seqops.binary_search([2, 3], 2) == 0
    assert seqops.binary_search([1, 2, 3], 4) == -1


def test_merge_sorted():
    assert seqops.merge_sorted([1, 3], [2, 4]) == [1, 2, 3, 4]
    assert seqops.merge_sorted([1, 2], [3, 4]) == [1, 2, 3, 4]


def test_remove_duplicates():
    assert seqops.remove_duplicates([3, 1, 2, 1, 3]) == [3, 1, 2]


def test_rotate():
    assert seqops.rotate([1, 2, 3, 4, 5], 2) == [3, 4, 5, 1, 2]
    assert seqops.rotate([1, 2, 3], 3) == [1, 2, 3]
    assert seqops.rotate([1, 2, 3], 5) == [3, 1, 2]


def test_partition():
    assert seqops.partition([3, 1, 2, 4], 2) == ([1, 2], [3, 4])


def test_flatten():
    assert seqops.flatten([[1, 2], [3, [4, 5]]]) == [1, 2, 3, 4, 5]
    assert seqops.flatten([[1], [2, 3]]) == [1, 2, 3]


def test_chunk():
    assert seqops.chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_max_subarray():
    assert seqops.max_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6
    assert seqops.max_subarray([-2, -1, -3]) == -1
'''

SEQOPS_TASKS = [
    {
        "id": "seqops-01",
        "test": "test_binary_search",
        "instruction": "Fix `binary_search` so it correctly finds a target at the very start of "
        "the list (the high bound is currently decremented past the target).",
        "difficulty": "hard",
        "category": "algorithm",
        "lines": 1,
        "fix": ("            hi = mid - 1", "            hi = mid"),
    },
    {
        "id": "seqops-02",
        "test": "test_merge_sorted",
        "instruction": "Fix `merge_sorted` so it appends the remaining elements of whichever list "
        "is not exhausted after the main merge loop.",
        "difficulty": "medium",
        "category": "algorithm",
        "lines": 2,
        "fix": (
            "    return out",
            "    out.extend(a[i:])\n    out.extend(b[j:])\n    return out",
        ),
    },
    {
        "id": "seqops-03",
        "test": "test_remove_duplicates",
        "instruction": "Fix `remove_duplicates` so it preserves the original order of first "
        "occurrences (using a set currently loses ordering).",
        "difficulty": "medium",
        "category": "algorithm",
        "lines": 5,
        "fix": (
            "    return list(set(seq))",
            "    seen = set()\n    out = []\n    for x in seq:\n        if x not in seen:\n            seen.add(x)\n            out.append(x)\n    return out",
        ),
    },
    {
        "id": "seqops-04",
        "test": "test_rotate",
        "instruction": "Fix `rotate` so it normalises k with a modulo, so k greater than the "
        "sequence length rotates correctly.",
        "difficulty": "easy",
        "category": "algorithm",
        "lines": 1,
        "fix": ("    return seq[k:] + seq[:k]", "    k = k % len(seq)\n    return seq[k:] + seq[:k]"),
    },
    {
        "id": "seqops-05",
        "test": "test_partition",
        "instruction": "Fix `partition` so elements equal to the pivot are included in the left "
        "partition (they are currently dropped).",
        "difficulty": "easy",
        "category": "algorithm",
        "lines": 1,
        "fix": ("    left = [x for x in seq if x < pivot]", "    left = [x for x in seq if x <= pivot]"),
    },
    {
        "id": "seqops-06",
        "test": "test_flatten",
        "instruction": "Fix `flatten` so it recursively flattens arbitrarily nested lists, not just "
        "a single level.",
        "difficulty": "hard",
        "category": "algorithm",
        "lines": 5,
        "fix": (
            "    return [item for sublist in nested for item in sublist]",
            "    out = []\n    for item in nested:\n        if isinstance(item, list):\n            out.extend(flatten(item))\n        else:\n            out.append(item)\n    return out",
        ),
    },
    {
        "id": "seqops-07",
        "test": "test_chunk",
        "instruction": "Fix `chunk` so it keeps the final partial chunk (the range currently stops "
        "short of the end).",
        "difficulty": "easy",
        "category": "algorithm",
        "lines": 1,
        "fix": (
            "for i in range(0, len(seq) - size, size)]",
            "for i in range(0, len(seq), size)]",
        ),
    },
    {
        "id": "seqops-08",
        "test": "test_max_subarray",
        "instruction": "Fix `max_subarray` so it handles all-negative arrays (initialising the best "
        "sum to 0 returns 0 instead of the largest negative number).",
        "difficulty": "medium",
        "category": "algorithm",
        "lines": 2,
        "fix": (
            "    best = 0\n    current = 0",
            "    best = nums[0]\n    current = nums[0]",
        ),
    },
]

# --------------------------------------------------------------------------- #
# fileops
# --------------------------------------------------------------------------- #

FILEOPS_MODULE = '''"""Small file I/O helpers (intentionally buggy for eval tasks)."""

import os


def read_lines(path):
    """Read a text file and return its lines without trailing newlines."""
    with open(path, encoding="utf-8") as f:
        return f.read().split()


def count_lines(path):
    """Count the number of lines in a text file."""
    with open(path, encoding="utf-8") as f:
        return len(f.read().split("\\n"))


def tail(path, n):
    """Return the last ``n`` lines of a text file."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    return lines[-n:]


def parse_kv(path):
    """Parse a 'key=value' file into a dict."""
    result = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            key, value = line.split("=")
            result[key] = value
    return result


def list_by_extension(directory, extension):
    """Return filenames in ``directory`` ending with ``extension`` (sorted)."""
    return sorted(f for f in os.listdir(directory) if f.endswith(extension))


def safe_write(path, content):
    """Write ``content`` to ``path``, creating the file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def read_csv_as_dicts(path):
    """Read a CSV file with a header row into a list of dicts."""
    import csv
    with open(path, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    return [dict(zip(header, row)) for row in rows]


def append_line(path, line):
    """Append ``line`` (plus a newline) to ``path``."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
'''

FILEOPS_TESTS = '''import fileops


def test_read_lines(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("hello world\\nfoo bar\\n")
    assert fileops.read_lines(str(p)) == ["hello world", "foo bar"]


def test_count_lines(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a\\nb\\nc\\n")
    assert fileops.count_lines(str(p)) == 3


def test_tail(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a\\nb\\nc\\nd\\n")
    assert fileops.tail(str(p), 2) == ["c", "d"]
    assert fileops.tail(str(p), 0) == []


def test_parse_kv(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("name=alice\\nurl=https://a.com?x=1\\n")
    assert fileops.parse_kv(str(p)) == {"name": "alice", "url": "https://a.com?x=1"}


def test_list_by_extension(tmp_path):
    (tmp_path / "a.txt").write_text("")
    (tmp_path / "b.TXT").write_text("")
    (tmp_path / "c.csv").write_text("")
    assert fileops.list_by_extension(str(tmp_path), ".txt") == ["a.txt", "b.TXT"]


def test_safe_write(tmp_path):
    target = tmp_path / "sub" / "f.txt"
    fileops.safe_write(str(target), "hello")
    assert target.read_text() == "hello"


def test_read_csv_as_dicts(tmp_path):
    p = tmp_path / "f.csv"
    p.write_text("name,age\\nAlice,30\\n")
    assert fileops.read_csv_as_dicts(str(p)) == [{"name": "Alice", "age": "30"}]


def test_append_line(tmp_path):
    p = tmp_path / "f.txt"
    fileops.append_line(str(p), "a")
    fileops.append_line(str(p), "b")
    assert p.read_text() == "a\\nb\\n"
'''

FILEOPS_TASKS = [
    {
        "id": "fileops-01",
        "test": "test_read_lines",
        "instruction": "Fix `read_lines` so it returns each line intact instead of splitting on "
        "every whitespace character (which merges words across lines).",
        "difficulty": "easy",
        "category": "file-io",
        "lines": 1,
        "fix": ("        return f.read().split()", "        return f.read().splitlines()"),
    },
    {
        "id": "fileops-02",
        "test": "test_count_lines",
        "instruction": "Fix `count_lines` so a trailing newline does not produce an extra phantom "
        "line count.",
        "difficulty": "easy",
        "category": "file-io",
        "lines": 1,
        "fix": ('return len(f.read().split("\\n"))', "return len(f.read().splitlines())"),
    },
    {
        "id": "fileops-03",
        "test": "test_tail",
        "instruction": "Fix `tail` so n=0 returns an empty list (the slice `[-0:]` currently "
        "returns the entire file).",
        "difficulty": "medium",
        "category": "file-io",
        "lines": 2,
        "fix": (
            "    return lines[-n:]",
            "    if n <= 0:\n        return []\n    return lines[-n:]",
        ),
    },
    {
        "id": "fileops-04",
        "test": "test_parse_kv",
        "instruction": "Fix `parse_kv` so a value containing '=' is preserved (split on the first "
        "'=' only, not every one).",
        "difficulty": "easy",
        "category": "file-io",
        "lines": 1,
        "fix": ('key, value = line.split("=")', 'key, value = line.split("=", 1)'),
    },
    {
        "id": "fileops-05",
        "test": "test_list_by_extension",
        "instruction": "Fix `list_by_extension` so the extension match is case-insensitive "
        "(a .TXT file should match '.txt').",
        "difficulty": "easy",
        "category": "file-io",
        "lines": 1,
        "fix": (
            "return sorted(f for f in os.listdir(directory) if f.endswith(extension))",
            "return sorted(f for f in os.listdir(directory) if f.lower().endswith(extension.lower()))",
        ),
    },
    {
        "id": "fileops-06",
        "test": "test_safe_write",
        "instruction": "Fix `safe_write` so it creates the parent directory of the target file "
        "before opening it (writing into a non-existent directory currently fails).",
        "difficulty": "medium",
        "category": "file-io",
        "lines": 2,
        "fix": (
            '    with open(path, "w", encoding="utf-8") as f:',
            '    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)\n    with open(path, "w", encoding="utf-8") as f:',
        ),
    },
    {
        "id": "fileops-07",
        "test": "test_read_csv_as_dicts",
        "instruction": "Fix `read_csv_as_dicts` so it skips the header row instead of turning it "
        "into a data record.",
        "difficulty": "medium",
        "category": "file-io",
        "lines": 1,
        "fix": ("    return [dict(zip(header, row)) for row in rows]", "    return [dict(zip(header, row)) for row in rows[1:]]"),
    },
    {
        "id": "fileops-08",
        "test": "test_append_line",
        "instruction": "Fix `append_line` so it writes a trailing newline after each line (successive "
        "appends currently concatenate onto one line).",
        "difficulty": "easy",
        "category": "file-io",
        "lines": 1,
        "fix": ('        f.write(line)', '        f.write(line + "\\n")'),
    },
]


# --------------------------------------------------------------------------- #

REPOS = {
    "textutils": {
        "module": TEXTUTILS_MODULE,
        "tests": TEXTUTILS_TESTS,
        "tasks": TEXTUTILS_TASKS,
    },
    "numstats": {
        "module": NUMSTATS_MODULE,
        "tests": NUMSTATS_TESTS,
        "tasks": NUMSTATS_TASKS,
    },
    "rpncalc": {
        "module": RPNCALC_MODULE,
        "tests": RPNCALC_TESTS,
        "tasks": RPNCALC_TASKS,
    },
    "datastore": {
        "module": DATASTORE_MODULE,
        "tests": DATASTORE_TESTS,
        "tasks": DATASTORE_TASKS,
    },
    "seqops": {
        "module": SEQOPS_MODULE,
        "tests": SEQOPS_TESTS,
        "tasks": SEQOPS_TASKS,
    },
    "fileops": {
        "module": FILEOPS_MODULE,
        "tests": FILEOPS_TESTS,
        "tasks": FILEOPS_TASKS,
    },
}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def build() -> list[dict]:
    """Materialise all repos + task JSONs. Returns the list of task dicts."""
    tasks: list[dict] = []
    for repo, spec in REPOS.items():
        module = spec["module"]
        repo_dir = REPOS_DIR / repo
        write_text(repo_dir / f"{repo}.py", module)
        write_text(repo_dir / "conftest.py", CONFTEST)
        write_text(repo_dir / "tests" / f"test_{repo}.py", spec["tests"])

        for t in spec["tasks"]:
            fixed = apply_fix(module, t["fix"][0], t["fix"][1])
            patch = make_patch(module, fixed, f"{repo}.py")
            if not patch:
                raise ValueError(f"empty gold_patch for {t['id']}")
            task = {
                "id": t["id"],
                "repo": repo,
                "instruction": t["instruction"],
                "gold_patch": patch,
                "test_command": (
                    f"python -m pytest tests/test_{repo}.py::{t['test']} -q"
                ),
                "repo_path": f"tasks/repos/{repo}",
                "metadata": {
                    "difficulty": t["difficulty"],
                    "category": t["category"],
                    "estimated_lines": t["lines"],
                },
            }
            write_text(TASKS_DIR / f"{t['id']}.json", json.dumps(task, indent=2, ensure_ascii=False) + "\n")
            tasks.append(task)
    return tasks


def run(cmd: list[str], cwd: Path, input_text: str | None = None):
    return subprocess.run(
        cmd, cwd=str(cwd), input=input_text, capture_output=True, text=True, timeout=180
    )


def verify(tasks: list[dict]) -> int:
    """Verify every task: buggy fails, patched passes. Returns number of failures."""
    failures = 0
    rows = []
    for task in tasks:
        repo = task["repo"]
        repo_dir = REPOS_DIR / repo
        # resolve the exact test name stored separately
        test_name = None
        for spec in REPOS[repo]["tasks"]:
            if spec["id"] == task["id"]:
                test_name = spec["test"]
                break
        assert test_name, task["id"]

        tmp = Path(tempfile.mkdtemp(prefix=f"minicodex-{task['id']}-"))
        try:
            shutil.copytree(repo_dir, tmp, dirs_exist_ok=True)

            sel = f"tests/test_{repo}.py::{test_name}"
            r1 = run([sys.executable, "-m", "pytest", sel, "-q"], tmp)
            buggy_fails = r1.returncode != 0

            # Send the patch as bytes: subprocess text mode would translate LF
            # to CRLF on Windows, causing a context mismatch against the LF files.
            r2 = subprocess.run(
                ["git", "apply", "-"],
                cwd=str(tmp),
                input=task["gold_patch"].encode("utf-8"),
                capture_output=True,
                timeout=180,
            )
            patch_ok = r2.returncode == 0

            r3 = run([sys.executable, "-m", "pytest", sel, "-q"], tmp)
            patched_passes = r3.returncode == 0

            ok = buggy_fails and patch_ok and patched_passes
            if not ok:
                failures += 1
                detail = []
                if not buggy_fails:
                    detail.append(f"BUGGY-TEST-UNEXPECTEDLY-PASSED (exit={r1.returncode})")
                if not patch_ok:
                    detail.append(f"GOLD-PATCH-APPLY-FAILED: {r2.stderr.decode('utf-8', 'replace').strip()[:300]}")
                if not patched_passes:
                    detail.append(f"PATCHED-TEST-FAILED (exit={r3.returncode}): {r3.stdout.strip()[:300]} {r3.stderr.strip()[:300]}")
                print(f"FAIL {task['id']}: {'; '.join(detail)}")
            rows.append((task["id"], buggy_fails, patch_ok, patched_passes))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print("\n== verification summary ==")
    print(f"{'task':<16} {'buggy_fails':<12} {'patch_ok':<9} {'patched_passes':<15}")
    for tid, bf, po, pp in rows:
        print(f"{tid:<16} {str(bf):<12} {str(po):<9} {str(pp):<15}")
    print(f"\n{len(rows) - failures}/{len(rows)} tasks verified correctly")
    return failures


def main() -> int:
    tasks = build()
    print(f"built {len(tasks)} tasks across {len(REPOS)} repos")
    return verify(tasks)


if __name__ == "__main__":
    sys.exit(main())
