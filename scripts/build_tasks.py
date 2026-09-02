"""Build the minicodex production task set (SWE-bench style) and verify it.

This script is the single source of truth for the hand-crafted repo-level tasks.
For each repo it defines a *correct* module, an expanded pytest suite covering
every function (edge cases included), and a list of tasks. Each task is a single
realistic bug injected into the correct module. Building materialises, per task:

  tasks/repos/<repo>/<task-id>/<repo>.py     # correct module with ONE bug
  tasks/repos/<repo>/<task-id>/conftest.py   # sys.path setup for pytest
  tasks/repos/<repo>/<task-id>/tests/test_<repo>.py  # full test suite

and a flat JSON file ``tasks/<id>.json`` carrying a ``fail_to_pass`` /
``pass_to_pass`` test matrix (SWE-bench contract) plus a real ``gold_patch``
(diff from the buggy module back to the correct module).

After building, every task is verified double-directionally with the shared
verifier (``minicodex.eval.verification.verify_gold_patch``):

  1. buggy baseline  -> every fail_to_pass test FAILS, every pass_to_pass PASSES
  2. apply gold_patch -> every fail_to_pass AND pass_to_pass test PASSES

Run:  uv run python scripts/build_tasks.py
"""

from __future__ import annotations

import difflib
import json
import shutil
import sys
from pathlib import Path

from minicodex.eval.task import Task
from minicodex.eval.verification import verify_gold_patch

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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# --------------------------------------------------------------------------- #
# textutils — string utilities
# --------------------------------------------------------------------------- #

TEXTUTILS_MODULE = '''"""Small string utility library (intentionally buggy for eval tasks)."""


def reverse_words(s):
    """Return the words of ``s`` in reverse order."""
    words = s.split()
    result = []
    for i in range(len(words) - 1, -1, -1):
        result.append(words[i])
    return " ".join(result)


def capitalize_words(s):
    """Capitalize the first letter of each word, preserving the rest."""
    return " ".join((w[:1].upper() + w[1:] if w else w) for w in s.split())


def count_vowels(s):
    """Count the vowels (a, e, i, o, u) in ``s``, case-insensitively."""
    return sum(1 for c in s if c.lower() in "aeiou")


def truncate(s, n):
    """Truncate ``s`` to ``n`` characters, appending '...' when truncated."""
    return s if len(s) <= n else s[:n] + "..."


def slugify(s):
    """Lowercase ``s`` and replace runs of whitespace with a single dash."""
    return "-".join(s.lower().split())


def camel_to_snake(s):
    """Convert ``CamelCase`` to ``snake_case``."""
    result = []
    for i, c in enumerate(s):
        if c.isupper() and i > 0:
            result.append("_")
        result.append(c.lower())
    return "".join(result)


def is_palindrome(s):
    """Return True if ``s`` is a palindrome ignoring case and spaces."""
    s = "".join(s.lower().split())
    return s == s[::-1]


def common_prefix(a, b):
    """Return the longest common prefix of ``a`` and ``b``."""
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    return a[:i]


def wrap(text, width):
    """Wrap ``text`` into lines of at most ``width`` characters."""
    return "\\n".join(text[i:i + width] for i in range(0, len(text), width))


def count_occurrences(text, sub):
    """Count non-overlapping occurrences of ``sub`` in ``text``."""
    if not sub:
        return 0
    count = 0
    i = 0
    while i < len(text):
        if text.startswith(sub, i):
            count += 1
            i += len(sub)
        else:
            i += 1
    return count
'''

TEXTUTILS_TESTS = '''import textutils


def test_reverse_words_two():
    assert textutils.reverse_words("hello world") == "world hello"


def test_reverse_words_three():
    assert textutils.reverse_words("a b c") == "c b a"


def test_reverse_words_single():
    assert textutils.reverse_words("single") == "single"


def test_capitalize_words_mixed():
    assert textutils.capitalize_words("hello WORLD") == "Hello WORLD"


def test_capitalize_words_camel():
    assert textutils.capitalize_words("fooBar baz") == "FooBar Baz"


def test_capitalize_words_simple():
    assert textutils.capitalize_words("hello world") == "Hello World"


def test_count_vowels_mixed():
    assert textutils.count_vowels("Hello wOrld") == 3


def test_count_vowels_upper():
    assert textutils.count_vowels("AEIOU") == 5


def test_count_vowels_lower():
    assert textutils.count_vowels("aeiou") == 5


def test_truncate_short():
    assert textutils.truncate("hello", 10) == "hello"


def test_truncate_exact():
    assert textutils.truncate("hello", 5) == "hello"


def test_truncate_long():
    assert textutils.truncate("hello world", 5) == "hello..."


def test_slugify_collapse():
    assert textutils.slugify("  Hello   World  ") == "hello-world"


def test_slugify_tab():
    assert textutils.slugify("a\\tb") == "a-b"


def test_slugify_simple():
    assert textutils.slugify("Hello World") == "hello-world"


def test_camel_to_snake_multi():
    assert textutils.camel_to_snake("HelloWorld") == "hello_world"


def test_camel_to_snake_single_upper():
    assert textutils.camel_to_snake("Hello") == "hello"


def test_camel_to_snake_lower():
    assert textutils.camel_to_snake("hello") == "hello"


def test_is_palindrome_case_space():
    assert textutils.is_palindrome("A man a plan a canal Panama") is True


def test_is_palindrome_space():
    assert textutils.is_palindrome("race car") is True


def test_is_palindrome_plain():
    assert textutils.is_palindrome("racecar") is True
    assert textutils.is_palindrome("hello") is False


def test_common_prefix_basic():
    assert textutils.common_prefix("abcdef", "abcxyz") == "abc"


def test_common_prefix_full():
    assert textutils.common_prefix("abc", "abc") == "abc"


def test_common_prefix_none():
    assert textutils.common_prefix("abc", "def") == ""


def test_wrap_basic():
    assert textutils.wrap("abcdef", 3) == "abc\\ndef"


def test_wrap_exact_width():
    assert textutils.wrap("hello", 5) == "hello"


def test_wrap_short():
    assert textutils.wrap("hello", 10) == "hello"


def test_count_occurrences_overlap():
    assert textutils.count_occurrences("aaaa", "aa") == 2


def test_count_occurrences_empty_sub():
    assert textutils.count_occurrences("hello", "") == 0


def test_count_occurrences_single():
    assert textutils.count_occurrences("hello", "l") == 2
'''

TEXTUTILS_TASKS = [
    {
        "id": "textutils-01",
        "instruction": "Fix `reverse_words` so it keeps the first word. It currently drops it because "
        "of an off-by-one in the loop range.",
        "difficulty": "medium",
        "category": "string",
        "lines": 1,
        "bug": ("for i in range(len(words) - 1, -1, -1):", "for i in range(len(words) - 1, 0, -1):"),
        "fail_to_pass": ["test_reverse_words_two", "test_reverse_words_three", "test_reverse_words_single"],
        "pass_to_pass": ["test_capitalize_words_simple", "test_slugify_simple", "test_common_prefix_basic"],
    },
    {
        "id": "textutils-02",
        "instruction": "Fix `capitalize_words` so it capitalizes the first letter of each word while "
        "preserving the remaining characters. `str.capitalize()` lowercases the rest.",
        "difficulty": "easy",
        "category": "string",
        "lines": 1,
        "bug": (
            '" ".join((w[:1].upper() + w[1:] if w else w) for w in s.split())',
            '" ".join(w.capitalize() for w in s.split())',
        ),
        "fail_to_pass": ["test_capitalize_words_mixed", "test_capitalize_words_camel"],
        "pass_to_pass": ["test_reverse_words_two", "test_slugify_simple", "test_truncate_short"],
    },
    {
        "id": "textutils-03",
        "instruction": "Fix `count_vowels` so it counts uppercase vowels as well as lowercase ones.",
        "difficulty": "easy",
        "category": "string",
        "lines": 1,
        "bug": ('return sum(1 for c in s if c.lower() in "aeiou")', 'return sum(1 for c in s if c in "aeiou")'),
        "fail_to_pass": ["test_count_vowels_mixed", "test_count_vowels_upper"],
        "pass_to_pass": ["test_reverse_words_two", "test_camel_to_snake_multi", "test_wrap_basic"],
    },
    {
        "id": "textutils-04",
        "instruction": "Fix `truncate` so it only appends '...' when the string is actually longer than "
        "n. It currently appends the ellipsis unconditionally.",
        "difficulty": "easy",
        "category": "string",
        "lines": 1,
        "bug": ('return s if len(s) <= n else s[:n] + "..."', 'return s[:n] + "..."'),
        "fail_to_pass": ["test_truncate_short", "test_truncate_exact"],
        "pass_to_pass": ["test_capitalize_words_simple", "test_slugify_simple", "test_common_prefix_basic"],
    },
    {
        "id": "textutils-05",
        "instruction": "Fix `slugify` so consecutive spaces collapse into a single dash and "
        "leading/trailing whitespace is removed.",
        "difficulty": "easy",
        "category": "string",
        "lines": 1,
        "bug": ('"-".join(s.lower().split())', 's.lower().replace(" ", "-")'),
        "fail_to_pass": ["test_slugify_collapse", "test_slugify_tab"],
        "pass_to_pass": ["test_reverse_words_two", "test_truncate_short", "test_count_occurrences_single"],
    },
    {
        "id": "textutils-06",
        "instruction": "Fix `camel_to_snake` so the first uppercase letter does not produce a leading "
        "underscore in the result.",
        "difficulty": "medium",
        "category": "string",
        "lines": 2,
        "bug": (
            "    for i, c in enumerate(s):\n        if c.isupper() and i > 0:\n            result.append(\"_\")",
            "    for c in s:\n        if c.isupper():\n            result.append(\"_\")",
        ),
        "fail_to_pass": ["test_camel_to_snake_multi", "test_camel_to_snake_single_upper"],
        "pass_to_pass": ["test_count_vowels_lower", "test_wrap_basic", "test_common_prefix_basic"],
    },
    {
        "id": "textutils-07",
        "instruction": "Fix `is_palindrome` so it ignores case and spaces when checking whether a string "
        "is a palindrome.",
        "difficulty": "medium",
        "category": "string",
        "lines": 2,
        "bug": (
            '    s = "".join(s.lower().split())\n    return s == s[::-1]',
            "    return s == s[::-1]",
        ),
        "fail_to_pass": ["test_is_palindrome_case_space", "test_is_palindrome_space"],
        "pass_to_pass": ["test_reverse_words_two", "test_slugify_simple", "test_truncate_short"],
    },
    {
        "id": "textutils-08",
        "instruction": "Fix `common_prefix` so it returns the full common prefix without dropping the "
        "last matching character (off-by-one in the return slice).",
        "difficulty": "medium",
        "category": "string",
        "lines": 1,
        "bug": ("    return a[:i]", "    return a[:i - 1]"),
        "fail_to_pass": ["test_common_prefix_basic", "test_common_prefix_full"],
        "pass_to_pass": ["test_reverse_words_two", "test_wrap_basic", "test_count_vowels_lower"],
    },
    {
        "id": "textutils-09",
        "instruction": "Fix `wrap` so each line contains the full `width` characters. It currently drops "
        "the last character of every line.",
        "difficulty": "easy",
        "category": "string",
        "lines": 1,
        "bug": ("text[i:i + width]", "text[i:i + width - 1]"),
        "fail_to_pass": ["test_wrap_basic", "test_wrap_exact_width"],
        "pass_to_pass": ["test_reverse_words_two", "test_truncate_short", "test_slugify_simple", "test_wrap_short"],
    },
    {
        "id": "textutils-10",
        "instruction": "Fix `count_occurrences` to count only non-overlapping occurrences and to handle an "
        "empty substring. It currently advances one character at a time even after a match and has no "
        "empty-substring guard.",
        "difficulty": "medium",
        "category": "string",
        "lines": 4,
        "bug": (
            "    if not sub:\n        return 0\n    count = 0\n    i = 0\n    while i < len(text):\n        if text.startswith(sub, i):\n            count += 1\n            i += len(sub)\n        else:\n            i += 1\n    return count",
            "    count = 0\n    i = 0\n    while i < len(text):\n        if text.startswith(sub, i):\n            count += 1\n        i += 1\n    return count",
        ),
        "fail_to_pass": ["test_count_occurrences_overlap", "test_count_occurrences_empty_sub"],
        "pass_to_pass": ["test_reverse_words_two", "test_wrap_basic", "test_camel_to_snake_lower"],
    },
]

# --------------------------------------------------------------------------- #
# numstats — numeric / statistics
# --------------------------------------------------------------------------- #

NUMSTATS_MODULE = '''"""Small numeric/statistics library (intentionally buggy for eval tasks)."""


def mean(values):
    """Return the arithmetic mean of ``values``."""
    if not values:
        raise ValueError("mean of empty sequence")
    return sum(values) / len(values)


def median(values):
    """Return the median of ``values``."""
    s = sorted(values)
    n = len(s)
    if n % 2 == 0:
        return (s[n // 2 - 1] + s[n // 2]) / 2
    return s[n // 2]


def mode(values):
    """Return the most frequent value in ``values``."""
    return max(set(values), key=values.count)


def variance(values):
    """Return the sample variance of ``values``."""
    m = sum(values) / len(values)
    return sum((x - m) ** 2 for x in values) / (len(values) - 1)


def percentile(values, p):
    """Return the ``p``-th percentile (0-100) of ``values``."""
    s = sorted(values)
    idx = min(int(len(s) * p / 100), len(s) - 1)
    return s[idx]


def moving_average(values, window):
    """Return the moving average of ``values`` over ``window``."""
    return [sum(values[i:i + window]) / window for i in range(len(values) - window + 1)]


def clamp(value, lo, hi):
    """Clamp ``value`` to the inclusive range [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def fibonacci(n):
    """Return the n-th Fibonacci number (fib(0)=0, fib(1)=1)."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def is_prime(n):
    """Return True if ``n`` is prime."""
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True


def gcd(a, b):
    """Return the greatest common divisor of ``a`` and ``b``."""
    while b:
        a, b = b, a % b
    return a
'''

NUMSTATS_TESTS = '''import pytest

import numstats


def test_mean_empty_raises():
    with pytest.raises(ValueError):
        numstats.mean([])


def test_mean_empty_raises_message():
    with pytest.raises(ValueError, match="empty"):
        numstats.mean([])


def test_mean_basic():
    assert numstats.mean([1, 2, 3, 4]) == 2.5


def test_median_even():
    assert numstats.median([1, 2, 3, 4]) == 2.5


def test_median_even_two():
    assert numstats.median([1, 2]) == 1.5


def test_median_odd():
    assert numstats.median([1, 2, 3]) == 2


def test_mode_basic():
    assert numstats.mode([1, 1, 2, 3]) == 1


def test_mode_strings():
    assert numstats.mode(["a", "b", "a"]) == "a"


def test_mode_single():
    assert numstats.mode([7]) == 7


def test_variance_basic():
    assert abs(numstats.variance([1, 2, 3, 4]) - 5 / 3) < 1e-9


def test_variance_two():
    assert abs(numstats.variance([1, 2]) - 0.5) < 1e-9


def test_percentile_max():
    assert numstats.percentile([1, 2, 3, 4, 5], 100) == 5


def test_percentile_full():
    assert numstats.percentile([1, 2], 100) == 2


def test_percentile_median():
    assert numstats.percentile([1, 2, 3, 4, 5], 50) == 3


def test_moving_average_basic():
    assert numstats.moving_average([1, 2, 3, 4, 5], 3) == [2.0, 3.0, 4.0]


def test_moving_average_window_two():
    assert numstats.moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]


def test_moving_average_window_one():
    assert numstats.moving_average([1, 2, 3], 1) == [1, 2, 3]


def test_clamp_low():
    assert numstats.clamp(0, 1, 10) == 1


def test_clamp_high():
    assert numstats.clamp(50, 1, 10) == 10


def test_clamp_in_range():
    assert numstats.clamp(5, 1, 10) == 5


def test_fibonacci_zero():
    assert numstats.fibonacci(0) == 0


def test_fibonacci_one():
    assert numstats.fibonacci(1) == 1


def test_fibonacci_nth():
    assert numstats.fibonacci(6) == 8


def test_is_prime_below_two():
    assert numstats.is_prime(1) is False
    assert numstats.is_prime(0) is False


def test_is_prime_negative():
    assert numstats.is_prime(-3) is False


def test_is_prime_two():
    assert numstats.is_prime(2) is True


def test_is_prime_composite_and_prime():
    assert numstats.is_prime(4) is False
    assert numstats.is_prime(17) is True


def test_gcd_basic():
    assert numstats.gcd(48, 18) == 6


def test_gcd_with_zero():
    assert numstats.gcd(0, 5) == 5


def test_gcd_swap():
    assert numstats.gcd(18, 48) == 6
'''

NUMSTATS_TASKS = [
    {
        "id": "numstats-01",
        "instruction": "Fix `mean` so it raises a `ValueError` for an empty input list instead of "
        "crashing with a division-by-zero error.",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 2,
        "bug": (
            '    if not values:\n        raise ValueError("mean of empty sequence")\n    return sum(values) / len(values)',
            "    return sum(values) / len(values)",
        ),
        "fail_to_pass": ["test_mean_empty_raises", "test_mean_empty_raises_message"],
        "pass_to_pass": ["test_median_odd", "test_variance_basic", "test_gcd_basic"],
    },
    {
        "id": "numstats-02",
        "instruction": "Fix `median` so it returns the average of the two middle elements for even-length "
        "inputs instead of only the upper-middle element.",
        "difficulty": "medium",
        "category": "numeric",
        "lines": 3,
        "bug": (
            "    if n % 2 == 0:\n        return (s[n // 2 - 1] + s[n // 2]) / 2\n    return s[n // 2]",
            "    return s[n // 2]",
        ),
        "fail_to_pass": ["test_median_even", "test_median_even_two"],
        "pass_to_pass": ["test_mean_basic", "test_variance_basic", "test_is_prime_two"],
    },
    {
        "id": "numstats-03",
        "instruction": "Fix `mode` so it returns the most frequent value itself rather than the frequency "
        "count.",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 1,
        "bug": ("return max(set(values), key=values.count)", "return max(values.count(v) for v in set(values))"),
        "fail_to_pass": ["test_mode_basic", "test_mode_strings"],
        "pass_to_pass": ["test_mean_basic", "test_median_odd", "test_gcd_basic"],
    },
    {
        "id": "numstats-04",
        "instruction": "Fix `variance` so it computes the sample variance (divide by n-1) rather than the "
        "population variance (divide by n).",
        "difficulty": "medium",
        "category": "numeric",
        "lines": 1,
        "bug": (
            "return sum((x - m) ** 2 for x in values) / (len(values) - 1)",
            "return sum((x - m) ** 2 for x in values) / len(values)",
        ),
        "fail_to_pass": ["test_variance_basic", "test_variance_two"],
        "pass_to_pass": ["test_mean_basic", "test_median_even", "test_is_prime_composite_and_prime"],
    },
    {
        "id": "numstats-05",
        "instruction": "Fix `percentile` so p=100 does not index past the end of the sorted list.",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 1,
        "bug": (
            "    idx = min(int(len(s) * p / 100), len(s) - 1)\n    return s[idx]",
            "    idx = int(len(s) * p / 100)\n    return s[idx]",
        ),
        "fail_to_pass": ["test_percentile_max", "test_percentile_full"],
        "pass_to_pass": ["test_mean_basic", "test_mode_basic", "test_gcd_basic", "test_percentile_median"],
    },
    {
        "id": "numstats-06",
        "instruction": "Fix `moving_average` so it only produces full windows of `window` elements (the "
        "current range over-iterates and emits trailing partial windows).",
        "difficulty": "medium",
        "category": "numeric",
        "lines": 1,
        "bug": (
            "for i in range(len(values) - window + 1)]",
            "for i in range(len(values))]",
        ),
        "fail_to_pass": ["test_moving_average_basic", "test_moving_average_window_two"],
        "pass_to_pass": ["test_mean_basic", "test_median_odd", "test_clamp_low", "test_moving_average_window_one"],
    },
    {
        "id": "numstats-07",
        "instruction": "Fix `clamp` so it returns the lower bound when the value is below the range and the "
        "upper bound when it is above (the two returns are currently swapped).",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 2,
        "bug": (
            "    if value < lo:\n        return lo\n    if value > hi:\n        return hi",
            "    if value < lo:\n        return hi\n    if value > hi:\n        return lo",
        ),
        "fail_to_pass": ["test_clamp_low", "test_clamp_high"],
        "pass_to_pass": ["test_mean_basic", "test_variance_basic", "test_gcd_basic"],
    },
    {
        "id": "numstats-08",
        "instruction": "Fix `fibonacci` so fib(0) returns 0 (the base case currently returns 1 for both 0 "
        "and 1).",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 1,
        "bug": ("    if n <= 1:\n        return n", "    if n <= 1:\n        return 1"),
        "fail_to_pass": ["test_fibonacci_zero", "test_fibonacci_nth"],
        "pass_to_pass": ["test_mean_basic", "test_is_prime_two", "test_gcd_basic"],
    },
    {
        "id": "numstats-09",
        "instruction": "Fix `is_prime` so it returns False for n less than 2 (1 and 0 are not prime).",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 2,
        "bug": (
            "    if n < 2:\n        return False\n    for i in range(2, int(n ** 0.5) + 1):",
            "    for i in range(2, int(n ** 0.5) + 1):",
        ),
        "fail_to_pass": ["test_is_prime_below_two", "test_is_prime_negative"],
        "pass_to_pass": ["test_mean_basic", "test_fibonacci_one", "test_gcd_basic", "test_is_prime_two"],
    },
    {
        "id": "numstats-10",
        "instruction": "Fix `gcd` so it returns the greatest common divisor (`a`) instead of always "
        "returning the remainder (`b`), which ends up as zero.",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 1,
        "bug": ("    return a", "    return b"),
        "fail_to_pass": ["test_gcd_basic", "test_gcd_with_zero"],
        "pass_to_pass": ["test_mean_basic", "test_median_odd", "test_is_prime_two"],
    },
]

# --------------------------------------------------------------------------- #
# rpncalc — reverse-polish-notation calculator
# --------------------------------------------------------------------------- #

RPNCALC_MODULE = '''"""Small reverse-polish-notation calculator (intentionally buggy for eval tasks)."""


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
    return str(int(value)) if value == int(value) else str(value)
'''

RPNCALC_TESTS = '''import pytest

import rpncalc


def test_is_number_float():
    assert rpncalc.is_number("3.5") is True


def test_is_number_negative():
    assert rpncalc.is_number("-2") is True


def test_is_number_int():
    assert rpncalc.is_number("3") is True


def test_is_number_operator():
    assert rpncalc.is_number("+") is False


def test_parse_number_float():
    assert rpncalc.parse_number("3.5") == 3.5


def test_parse_number_negative_float():
    assert rpncalc.parse_number("-2.5") == -2.5


def test_parse_number_int():
    assert rpncalc.parse_number("3") == 3


def test_apply_divide_float():
    assert rpncalc.apply("/", 7, 2) == 3.5


def test_apply_divide_fraction():
    assert rpncalc.apply("/", 1, 4) == 0.25


def test_apply_add():
    assert rpncalc.apply("+", 2, 3) == 5


def test_safe_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        rpncalc.safe_divide(1, 0)


def test_safe_divide_zero_dividend():
    with pytest.raises(ZeroDivisionError):
        rpncalc.safe_divide(0, 0)


def test_safe_divide_basic():
    assert rpncalc.safe_divide(6, 3) == 2.0


def test_precedence_mul_tighter():
    assert rpncalc.precedence("*") > rpncalc.precedence("+")


def test_precedence_div_tighter():
    assert rpncalc.precedence("/") > rpncalc.precedence("-")


def test_precedence_div_equals_mul():
    assert rpncalc.precedence("/") == rpncalc.precedence("*")


def test_tokenize_multi():
    assert rpncalc.tokenize("12 3 +") == ["12", "3", "+"]


def test_tokenize_multi_two():
    assert rpncalc.tokenize("5 10 -") == ["5", "10", "-"]


def test_tokenize_single():
    assert rpncalc.tokenize("7") == ["7"]


def test_evaluate_subtraction():
    assert rpncalc.evaluate(["5", "3", "-"]) == 2


def test_evaluate_division():
    assert rpncalc.evaluate(["8", "2", "/"]) == 4.0


def test_evaluate_addition():
    assert rpncalc.evaluate(["2", "3", "+"]) == 5


def test_format_number_float():
    assert rpncalc.format_number(3.5) == "3.5"


def test_format_number_negative_float():
    assert rpncalc.format_number(-2.5) == "-2.5"


def test_format_number_int():
    assert rpncalc.format_number(3) == "3"
'''

RPNCALC_TASKS = [
    {
        "id": "rpncalc-01",
        "instruction": "Fix `is_number` so it recognises floats and negative numbers, not just all-digit "
        "strings.",
        "difficulty": "easy",
        "category": "parsing",
        "lines": 3,
        "bug": (
            "    try:\n        float(token)\n        return True\n    except ValueError:\n        return False",
            "    return token.isdigit()",
        ),
        "fail_to_pass": ["test_is_number_float", "test_is_number_negative"],
        "pass_to_pass": ["test_tokenize_multi", "test_precedence_mul_tighter", "test_format_number_int"],
    },
    {
        "id": "rpncalc-02",
        "instruction": "Fix `parse_number` so it parses floats (e.g. \"3.5\") instead of only integers.",
        "difficulty": "easy",
        "category": "parsing",
        "lines": 1,
        "bug": (
            'return float(token) if "." in token else int(token)',
            "return int(token)",
        ),
        "fail_to_pass": ["test_parse_number_float", "test_parse_number_negative_float"],
        "pass_to_pass": ["test_tokenize_single", "test_safe_divide_basic", "test_format_number_int", "test_parse_number_int"],
    },
    {
        "id": "rpncalc-03",
        "instruction": "Fix `apply` so the division operator returns a float result instead of truncating "
        "with integer floor division.",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 1,
        "bug": ("        return a / b", "        return a // b"),
        "fail_to_pass": ["test_apply_divide_float", "test_apply_divide_fraction"],
        "pass_to_pass": ["test_safe_divide_basic", "test_tokenize_single", "test_format_number_int", "test_apply_add"],
    },
    {
        "id": "rpncalc-04",
        "instruction": "Fix `safe_divide` so it raises `ZeroDivisionError` on division by zero instead of "
        "silently returning 0.",
        "difficulty": "easy",
        "category": "edge-case",
        "lines": 2,
        "bug": (
            '    if b == 0:\n        raise ZeroDivisionError("division by zero")\n    return a / b',
            "    if b == 0:\n        return 0\n    return a / b",
        ),
        "fail_to_pass": ["test_safe_divide_by_zero", "test_safe_divide_zero_dividend"],
        "pass_to_pass": ["test_apply_add", "test_tokenize_single", "test_precedence_mul_tighter", "test_safe_divide_basic"],
    },
    {
        "id": "rpncalc-05",
        "instruction": "Fix `precedence` so multiplication and division bind tighter (higher value) than "
        "addition and subtraction.",
        "difficulty": "easy",
        "category": "parsing",
        "lines": 1,
        "bug": (
            'return {"+": 1, "-": 1, "*": 2, "/": 2}[op]',
            'return {"+": 1, "-": 1, "*": 1, "/": 1}[op]',
        ),
        "fail_to_pass": ["test_precedence_mul_tighter", "test_precedence_div_tighter"],
        "pass_to_pass": ["test_tokenize_single", "test_safe_divide_basic", "test_format_number_int", "test_precedence_div_equals_mul"],
    },
    {
        "id": "rpncalc-06",
        "instruction": "Fix `tokenize` so it splits on whitespace and keeps multi-character numbers intact "
        "(it currently splits every character).",
        "difficulty": "easy",
        "category": "parsing",
        "lines": 1,
        "bug": ("return expr.split()", 'return list(expr.replace(" ", ""))'),
        "fail_to_pass": ["test_tokenize_multi", "test_tokenize_multi_two"],
        "pass_to_pass": ["test_is_number_int", "test_safe_divide_basic", "test_format_number_int", "test_tokenize_single"],
    },
    {
        "id": "rpncalc-07",
        "instruction": "Fix `evaluate` so it pops the operands in the correct order for non-commutative "
        "operators (subtraction and division currently produce reversed results).",
        "difficulty": "medium",
        "category": "algorithm",
        "lines": 2,
        "bug": (
            "            b = stack.pop()\n            a = stack.pop()\n            stack.append(apply(token, a, b))",
            "            a = stack.pop()\n            b = stack.pop()\n            stack.append(apply(token, a, b))",
        ),
        "fail_to_pass": ["test_evaluate_subtraction", "test_evaluate_division"],
        "pass_to_pass": ["test_tokenize_single", "test_safe_divide_basic", "test_format_number_int", "test_evaluate_addition"],
    },
    {
        "id": "rpncalc-08",
        "instruction": "Fix `format_number` so it preserves the fractional part for non-integer values "
        "instead of truncating with int().",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 1,
        "bug": ("return str(int(value)) if value == int(value) else str(value)", "return str(int(value))"),
        "fail_to_pass": ["test_format_number_float", "test_format_number_negative_float"],
        "pass_to_pass": ["test_tokenize_single", "test_safe_divide_basic", "test_is_number_int", "test_format_number_int"],
    },
]

# --------------------------------------------------------------------------- #
# datastore — JSON/CSV data utilities
# --------------------------------------------------------------------------- #

DATASTORE_MODULE = '''"""Small JSON/CSV data utilities (intentionally buggy for eval tasks)."""

import json


def parse_json(text):
    """Parse a JSON string into a Python object."""
    if not text.strip():
        return {}
    return json.loads(text)


def parse_csv(text):
    """Parse a CSV string into a list of rows (lists of fields)."""
    return [[f.strip() for f in line.split(",")] for line in text.splitlines()]


def filter_records(records, key, value):
    """Return records whose ``key`` equals ``value``."""
    return [r for r in records if r.get(key) == value]


def group_by(records, key):
    """Group records by the value of ``key`` (missing key -> 'unknown')."""
    groups = {}
    for r in records:
        groups.setdefault(r.get(key, "unknown"), []).append(r)
    return groups


def to_csv(rows, delimiter=","):
    """Serialize a list of rows into a CSV string using ``delimiter``."""
    return "\\n".join(delimiter.join(map(str, row)) for row in rows)


def summarize(values):
    """Sum a list of numeric strings/values into a float."""
    total = 0.0
    for v in values:
        total += float(v)
    return total


def nested_get(obj, path):
    """Return the value at a dotted ``path`` (e.g. 'a.b.c') or None if missing."""
    for part in path.split("."):
        if not isinstance(obj, dict) or part not in obj:
            return None
        obj = obj[part]
    return obj


def dedupe(records, key):
    """Remove records with duplicate ``key`` values, keeping the first."""
    seen = set()
    out = []
    for r in records:
        if r[key] not in seen:
            out.append(r)
        seen.add(r[key])
    return out
'''

DATASTORE_TESTS = '''import datastore


def test_parse_json_empty():
    assert datastore.parse_json("") == {}


def test_parse_json_whitespace():
    assert datastore.parse_json("   ") == {}


def test_parse_json_object():
    assert datastore.parse_json('{"a": 1}') == {"a": 1}


def test_parse_csv_strips():
    assert datastore.parse_csv("a, b\\n1, 2") == [["a", "b"], ["1", "2"]]


def test_parse_csv_extra_spaces():
    assert datastore.parse_csv(" x , y ") == [["x", "y"]]


def test_filter_records_match():
    records = [{"k": 1}, {"k": 2}, {"k": 1}]
    assert datastore.filter_records(records, "k", 1) == [{"k": 1}, {"k": 1}]


def test_filter_records_no_match():
    records = [{"k": 1}, {"k": 2}]
    assert datastore.filter_records(records, "k", 9) == []


def test_group_by_missing_key():
    records = [{"v": 2}]
    assert datastore.group_by(records, "k") == {"unknown": [{"v": 2}]}


def test_group_by_present():
    records = [{"k": "a", "v": 1}, {"v": 2}, {"k": "a", "v": 3}]
    assert datastore.group_by(records, "k")["a"] == [{"k": "a", "v": 1}, {"k": "a", "v": 3}]


def test_to_csv_custom_delimiter():
    assert datastore.to_csv([["a", "b"]], delimiter=";") == "a;b"


def test_to_csv_custom_pipe():
    assert datastore.to_csv([["a", "b"]], delimiter="|") == "a|b"


def test_to_csv_default():
    assert datastore.to_csv([["a", "b"], ["c", "d"]]) == "a,b\\nc,d"


def test_summarize_floats():
    assert datastore.summarize(["1.5", "2.5"]) == 4.0


def test_summarize_mixed():
    assert datastore.summarize(["1", "2.5"]) == 3.5


def test_summarize_ints():
    assert datastore.summarize([1, 2, 3]) == 6.0


def test_nested_get_missing():
    assert datastore.nested_get({"a": {}}, "a.b.c") is None


def test_nested_get_deep_missing():
    assert datastore.nested_get({"a": {"b": 1}}, "a.x.y") is None


def test_nested_get_present():
    assert datastore.nested_get({"a": {"b": 1}}, "a.b") == 1


def test_dedupe_keeps_first():
    records = [{"id": 1, "v": "a"}, {"id": 1, "v": "b"}, {"id": 2, "v": "c"}]
    assert datastore.dedupe(records, "id") == [{"id": 1, "v": "a"}, {"id": 2, "v": "c"}]


def test_dedupe_all_unique():
    records = [{"id": 1}, {"id": 2}]
    assert datastore.dedupe(records, "id") == [{"id": 1}, {"id": 2}]
'''

DATASTORE_TASKS = [
    {
        "id": "datastore-01",
        "instruction": "Fix `parse_json` so an empty string parses to an empty dict instead of raising a "
        "JSON decode error.",
        "difficulty": "easy",
        "category": "data",
        "lines": 2,
        "bug": (
            "    if not text.strip():\n        return {}\n    return json.loads(text)",
            "    return json.loads(text)",
        ),
        "fail_to_pass": ["test_parse_json_empty", "test_parse_json_whitespace"],
        "pass_to_pass": ["test_parse_csv_strips", "test_filter_records_match", "test_to_csv_default"],
    },
    {
        "id": "datastore-02",
        "instruction": "Fix `parse_csv` so each field is stripped of surrounding whitespace.",
        "difficulty": "easy",
        "category": "data",
        "lines": 1,
        "bug": (
            'return [[f.strip() for f in line.split(",")] for line in text.splitlines()]',
            'return [line.split(",") for line in text.splitlines()]',
        ),
        "fail_to_pass": ["test_parse_csv_strips", "test_parse_csv_extra_spaces"],
        "pass_to_pass": ["test_parse_json_object", "test_summarize_floats", "test_dedupe_keeps_first"],
    },
    {
        "id": "datastore-03",
        "instruction": "Fix `filter_records` so it keeps records whose key equals the given value (the "
        "comparison operator is currently inverted).",
        "difficulty": "easy",
        "category": "data",
        "lines": 1,
        "bug": ("return [r for r in records if r.get(key) == value]", "return [r for r in records if r.get(key) != value]"),
        "fail_to_pass": ["test_filter_records_match", "test_filter_records_no_match"],
        "pass_to_pass": ["test_parse_csv_strips", "test_group_by_present", "test_to_csv_default"],
    },
    {
        "id": "datastore-04",
        "instruction": "Fix `group_by` so records missing the key are grouped under 'unknown' instead of "
        "raising a KeyError.",
        "difficulty": "medium",
        "category": "data",
        "lines": 1,
        "bug": (
            'groups.setdefault(r.get(key, "unknown"), []).append(r)',
            "groups.setdefault(r[key], []).append(r)",
        ),
        "fail_to_pass": ["test_group_by_missing_key", "test_group_by_present"],
        "pass_to_pass": ["test_parse_json_object", "test_filter_records_match", "test_dedupe_keeps_first"],
    },
    {
        "id": "datastore-05",
        "instruction": "Fix `to_csv` so it honours the `delimiter` argument instead of always joining with "
        "a comma.",
        "difficulty": "medium",
        "category": "data",
        "lines": 1,
        "bug": ("delimiter.join(map(str, row))", '",".join(map(str, row))'),
        "fail_to_pass": ["test_to_csv_custom_delimiter", "test_to_csv_custom_pipe"],
        "pass_to_pass": ["test_parse_csv_strips", "test_summarize_floats", "test_nested_get_present", "test_to_csv_default"],
    },
    {
        "id": "datastore-06",
        "instruction": "Fix `summarize` so it sums floats (e.g. \"1.5\") instead of coercing every value "
        "with int() and crashing on decimals.",
        "difficulty": "easy",
        "category": "numeric",
        "lines": 1,
        "bug": ("        total += float(v)", "        total += int(v)"),
        "fail_to_pass": ["test_summarize_floats", "test_summarize_mixed"],
        "pass_to_pass": ["test_parse_json_object", "test_to_csv_default", "test_dedupe_keeps_first", "test_summarize_ints"],
    },
    {
        "id": "datastore-07",
        "instruction": "Fix `nested_get` so it returns None when a key in the dotted path is missing "
        "instead of raising a KeyError.",
        "difficulty": "hard",
        "category": "data",
        "lines": 7,
        "bug": (
            "    for part in path.split(\".\"):\n        if not isinstance(obj, dict) or part not in obj:\n            return None\n        obj = obj[part]\n    return obj",
            "    for part in path.split(\".\"):\n        obj = obj[part]\n    return obj",
        ),
        "fail_to_pass": ["test_nested_get_missing", "test_nested_get_deep_missing"],
        "pass_to_pass": ["test_parse_json_object", "test_filter_records_match", "test_summarize_floats", "test_nested_get_present"],
    },
    {
        "id": "datastore-08",
        "instruction": "Fix `dedupe` so it keeps the first occurrence of each key (it currently keeps the "
        "duplicates instead).",
        "difficulty": "medium",
        "category": "data",
        "lines": 2,
        "bug": (
            "        if r[key] not in seen:\n            out.append(r)\n        seen.add(r[key])",
            "        if r[key] in seen:\n            out.append(r)\n        seen.add(r[key])",
        ),
        "fail_to_pass": ["test_dedupe_keeps_first", "test_dedupe_all_unique"],
        "pass_to_pass": ["test_parse_json_object", "test_filter_records_match", "test_to_csv_default"],
    },
]

# --------------------------------------------------------------------------- #
# seqops — sequence algorithms
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
            hi = mid
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
    out.extend(a[i:])
    out.extend(b[j:])
    return out


def remove_duplicates(seq):
    """Return ``seq`` with duplicates removed, preserving order."""
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def rotate(seq, k):
    """Rotate ``seq`` to the left by ``k`` positions."""
    k = k % len(seq)
    return seq[k:] + seq[:k]


def partition(seq, pivot):
    """Return (left, right) where left <= pivot < right."""
    left = [x for x in seq if x <= pivot]
    right = [x for x in seq if x > pivot]
    return left, right


def flatten(nested):
    """Flatten a nested list of lists into a single list."""
    out = []
    for item in nested:
        if isinstance(item, list):
            out.extend(flatten(item))
        else:
            out.append(item)
    return out


def chunk(seq, size):
    """Split ``seq`` into chunks of ``size``."""
    return [seq[i:i + size] for i in range(0, len(seq), size)]


def max_subarray(nums):
    """Return the maximum subarray sum (Kadane's algorithm)."""
    best = nums[0]
    current = nums[0]
    for x in nums[1:]:
        current = max(x, current + x)
        best = max(best, current)
    return best
'''

SEQOPS_TESTS = '''import seqops


def test_binary_search_first():
    assert seqops.binary_search([2, 3], 2) == 0


def test_binary_search_left():
    assert seqops.binary_search([1, 2, 3, 4], 2) == 1


def test_binary_search_middle():
    assert seqops.binary_search([1, 2, 3, 4, 5], 3) == 2


def test_binary_search_missing():
    assert seqops.binary_search([1, 2, 3], 4) == -1


def test_merge_sorted_one_exhausted():
    assert seqops.merge_sorted([1, 2], [3, 4]) == [1, 2, 3, 4]


def test_merge_sorted_interleaved():
    assert seqops.merge_sorted([1, 3], [2, 4]) == [1, 2, 3, 4]


def test_remove_duplicates_order():
    assert seqops.remove_duplicates([3, 1, 2, 1, 3]) == [3, 1, 2]


def test_remove_duplicates_order_two():
    assert seqops.remove_duplicates([5, 3, 5, 2, 3]) == [5, 3, 2]


def test_remove_duplicates_no_dupes():
    assert seqops.remove_duplicates([1, 2, 3]) == [1, 2, 3]


def test_rotate_wraparound():
    assert seqops.rotate([1, 2, 3], 5) == [3, 1, 2]


def test_rotate_wraparound_two():
    assert seqops.rotate([1, 2, 3], 4) == [2, 3, 1]


def test_rotate_full():
    assert seqops.rotate([1, 2, 3], 3) == [1, 2, 3]


def test_rotate_basic():
    assert seqops.rotate([1, 2, 3, 4, 5], 2) == [3, 4, 5, 1, 2]


def test_partition_equal_pivot():
    assert seqops.partition([1, 2, 2, 3], 2) == ([1, 2, 2], [3])


def test_partition_basic():
    assert seqops.partition([3, 1, 2, 4], 2) == ([1, 2], [3, 4])


def test_flatten_deep():
    assert seqops.flatten([[1, 2], [3, [4, 5]]]) == [1, 2, 3, 4, 5]


def test_flatten_deeper():
    assert seqops.flatten([[1, [2, [3]]]]) == [1, 2, 3]


def test_flatten_shallow():
    assert seqops.flatten([[1], [2, 3]]) == [1, 2, 3]


def test_chunk_partial():
    assert seqops.chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_chunk_exact():
    assert seqops.chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_max_subarray_all_negative():
    assert seqops.max_subarray([-2, -1, -3]) == -1


def test_max_subarray_single_negative():
    assert seqops.max_subarray([-5]) == -5


def test_max_subarray_positive():
    assert seqops.max_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6
'''

SEQOPS_TASKS = [
    {
        "id": "seqops-01",
        "instruction": "Fix `binary_search` so it correctly finds a target at the very start of the list "
        "(the high bound is currently decremented past the target).",
        "difficulty": "hard",
        "category": "algorithm",
        "lines": 1,
        "bug": ("            hi = mid", "            hi = mid - 1"),
        "fail_to_pass": ["test_binary_search_first", "test_binary_search_left"],
        "pass_to_pass": ["test_merge_sorted_interleaved", "test_rotate_basic", "test_chunk_partial", "test_binary_search_middle"],
    },
    {
        "id": "seqops-02",
        "instruction": "Fix `merge_sorted` so it appends the remaining elements of whichever list is not "
        "exhausted after the main merge loop.",
        "difficulty": "medium",
        "category": "algorithm",
        "lines": 2,
        "bug": (
            "    out.extend(a[i:])\n    out.extend(b[j:])\n    return out",
            "    return out",
        ),
        "fail_to_pass": ["test_merge_sorted_one_exhausted", "test_merge_sorted_interleaved"],
        "pass_to_pass": ["test_binary_search_middle", "test_rotate_basic", "test_max_subarray_positive"],
    },
    {
        "id": "seqops-03",
        "instruction": "Fix `remove_duplicates` so it preserves the original order of first occurrences "
        "(using a set currently loses ordering).",
        "difficulty": "medium",
        "category": "algorithm",
        "lines": 5,
        "bug": (
            "    seen = set()\n    out = []\n    for x in seq:\n        if x not in seen:\n            seen.add(x)\n            out.append(x)\n    return out",
            "    return list(set(seq))",
        ),
        "fail_to_pass": ["test_remove_duplicates_order", "test_remove_duplicates_order_two"],
        "pass_to_pass": ["test_merge_sorted_interleaved", "test_chunk_partial", "test_flatten_shallow", "test_remove_duplicates_no_dupes"],
    },
    {
        "id": "seqops-04",
        "instruction": "Fix `rotate` so it normalises k with a modulo, so k greater than the sequence "
        "length rotates correctly.",
        "difficulty": "easy",
        "category": "algorithm",
        "lines": 1,
        "bug": ("    k = k % len(seq)\n    return seq[k:] + seq[:k]", "    return seq[k:] + seq[:k]"),
        "fail_to_pass": ["test_rotate_wraparound", "test_rotate_wraparound_two"],
        "pass_to_pass": ["test_merge_sorted_interleaved", "test_partition_basic", "test_chunk_partial", "test_rotate_basic"],
    },
    {
        "id": "seqops-05",
        "instruction": "Fix `partition` so elements equal to the pivot are included in the left partition "
        "(they are currently dropped).",
        "difficulty": "easy",
        "category": "algorithm",
        "lines": 1,
        "bug": ("    left = [x for x in seq if x <= pivot]", "    left = [x for x in seq if x < pivot]"),
        "fail_to_pass": ["test_partition_equal_pivot", "test_partition_basic"],
        "pass_to_pass": ["test_rotate_basic", "test_chunk_partial", "test_flatten_shallow"],
    },
    {
        "id": "seqops-06",
        "instruction": "Fix `flatten` so it recursively flattens arbitrarily nested lists, not just a "
        "single level.",
        "difficulty": "hard",
        "category": "algorithm",
        "lines": 5,
        "bug": (
            "    out = []\n    for item in nested:\n        if isinstance(item, list):\n            out.extend(flatten(item))\n        else:\n            out.append(item)\n    return out",
            "    return [item for sublist in nested for item in sublist]",
        ),
        "fail_to_pass": ["test_flatten_deep", "test_flatten_deeper"],
        "pass_to_pass": ["test_rotate_basic", "test_chunk_partial", "test_merge_sorted_interleaved", "test_flatten_shallow"],
    },
    {
        "id": "seqops-07",
        "instruction": "Fix `chunk` so it keeps the final partial chunk (the range currently stops short "
        "of the end).",
        "difficulty": "easy",
        "category": "algorithm",
        "lines": 1,
        "bug": ("for i in range(0, len(seq), size)]", "for i in range(0, len(seq) - size, size)]"),
        "fail_to_pass": ["test_chunk_partial", "test_chunk_exact"],
        "pass_to_pass": ["test_rotate_basic", "test_partition_basic", "test_flatten_shallow"],
    },
    {
        "id": "seqops-08",
        "instruction": "Fix `max_subarray` so it handles all-negative arrays (initialising the best sum to "
        "0 returns 0 instead of the largest negative number).",
        "difficulty": "medium",
        "category": "algorithm",
        "lines": 2,
        "bug": (
            "    best = nums[0]\n    current = nums[0]\n    for x in nums[1:]:",
            "    best = 0\n    current = 0\n    for x in nums:",
        ),
        "fail_to_pass": ["test_max_subarray_all_negative", "test_max_subarray_single_negative"],
        "pass_to_pass": ["test_rotate_basic", "test_binary_search_middle", "test_chunk_partial", "test_max_subarray_positive"],
    },
]

# --------------------------------------------------------------------------- #
# fileops — file I/O helpers
# --------------------------------------------------------------------------- #

FILEOPS_MODULE = '''"""Small file I/O helpers (intentionally buggy for eval tasks)."""

import csv
import os


def read_lines(path):
    """Read a text file and return its lines without trailing newlines."""
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def count_lines(path):
    """Count the number of lines in a text file."""
    with open(path, encoding="utf-8") as f:
        return len(f.read().splitlines())


def tail(path, n):
    """Return the last ``n`` lines of a text file."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    if n <= 0:
        return []
    return lines[-n:]


def parse_kv(path):
    """Parse a 'key=value' file into a dict."""
    result = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            key, value = line.split("=", 1)
            result[key] = value
    return result


def list_by_extension(directory, extension):
    """Return filenames in ``directory`` ending with ``extension`` (sorted)."""
    return sorted(f for f in os.listdir(directory) if f.lower().endswith(extension.lower()))


def safe_write(path, content):
    """Write ``content`` to ``path``, creating the parent directory."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def read_csv_as_dicts(path):
    """Read a CSV file with a header row into a list of dicts."""
    with open(path, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    return [dict(zip(header, row)) for row in rows[1:]]


def append_line(path, line):
    """Append ``line`` (plus a newline) to ``path``."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\\n")
'''

FILEOPS_TESTS = '''import fileops


def test_read_lines_basic(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("hello world\\nfoo bar\\n", encoding="utf-8")
    assert fileops.read_lines(str(p)) == ["hello world", "foo bar"]


def test_read_lines_words(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("one two\\nthree\\n", encoding="utf-8")
    assert fileops.read_lines(str(p)) == ["one two", "three"]


def test_read_lines_no_trailing_newline(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("hello\\nworld", encoding="utf-8")
    assert fileops.read_lines(str(p)) == ["hello", "world"]


def test_count_lines_basic(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a\\nb\\nc\\n", encoding="utf-8")
    assert fileops.count_lines(str(p)) == 3


def test_count_lines_empty(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("", encoding="utf-8")
    assert fileops.count_lines(str(p)) == 0


def test_tail_zero(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a\\nb\\n", encoding="utf-8")
    assert fileops.tail(str(p), 0) == []


def test_tail_negative(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a\\nb\\n", encoding="utf-8")
    assert fileops.tail(str(p), -1) == []


def test_tail_basic(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a\\nb\\nc\\nd\\n", encoding="utf-8")
    assert fileops.tail(str(p), 2) == ["c", "d"]


def test_parse_kv_value_with_equals(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("url=https://a.com?x=1\\n", encoding="utf-8")
    assert fileops.parse_kv(str(p)) == {"url": "https://a.com?x=1"}


def test_parse_kv_multiple_equals(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a=b=c\\n", encoding="utf-8")
    assert fileops.parse_kv(str(p)) == {"a": "b=c"}


def test_parse_kv_basic(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a=1\\nb=2\\n", encoding="utf-8")
    assert fileops.parse_kv(str(p)) == {"a": "1", "b": "2"}


def test_list_by_extension_case(tmp_path):
    (tmp_path / "a.txt").write_text("")
    (tmp_path / "b.TXT").write_text("")
    (tmp_path / "c.csv").write_text("")
    assert fileops.list_by_extension(str(tmp_path), ".txt") == ["a.txt", "b.TXT"]


def test_list_by_extension_upper_only(tmp_path):
    (tmp_path / "DATA.TXT").write_text("")
    assert fileops.list_by_extension(str(tmp_path), ".txt") == ["DATA.TXT"]


def test_list_by_extension_empty(tmp_path):
    (tmp_path / "a.txt").write_text("")
    assert fileops.list_by_extension(str(tmp_path), ".csv") == []


def test_safe_write_creates_parent(tmp_path):
    target = tmp_path / "sub" / "f.txt"
    fileops.safe_write(str(target), "hello")
    assert target.read_text(encoding="utf-8") == "hello"


def test_safe_write_deep_parent(tmp_path):
    target = tmp_path / "a" / "b" / "c" / "f.txt"
    fileops.safe_write(str(target), "deep")
    assert target.read_text(encoding="utf-8") == "deep"


def test_safe_write_overwrites(tmp_path):
    target = tmp_path / "f.txt"
    fileops.safe_write(str(target), "one")
    fileops.safe_write(str(target), "two")
    assert target.read_text(encoding="utf-8") == "two"


def test_read_csv_as_dicts_skips_header(tmp_path):
    p = tmp_path / "f.csv"
    p.write_text("name,age\\nAlice,30\\nBob,40\\n", encoding="utf-8")
    rows = fileops.read_csv_as_dicts(str(p))
    assert rows == [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "40"}]


def test_read_csv_as_dicts_basic(tmp_path):
    p = tmp_path / "f.csv"
    p.write_text("name,age\\nAlice,30\\n", encoding="utf-8")
    assert fileops.read_csv_as_dicts(str(p)) == [{"name": "Alice", "age": "30"}]


def test_append_line_basic(tmp_path):
    p = tmp_path / "f.txt"
    fileops.append_line(str(p), "a")
    fileops.append_line(str(p), "b")
    assert p.read_text(encoding="utf-8") == "a\\nb\\n"


def test_append_line_creates_file(tmp_path):
    p = tmp_path / "f.txt"
    fileops.append_line(str(p), "hello")
    assert p.read_text(encoding="utf-8") == "hello\\n"
'''

FILEOPS_TASKS = [
    {
        "id": "fileops-01",
        "instruction": "Fix `read_lines` so it returns each line intact instead of splitting on every "
        "whitespace character (which merges words across lines).",
        "difficulty": "easy",
        "category": "file-io",
        "lines": 1,
        "bug": ("        return f.read().splitlines()", "        return f.read().split()"),
        "fail_to_pass": ["test_read_lines_basic", "test_read_lines_words"],
        "pass_to_pass": ["test_count_lines_basic", "test_tail_basic", "test_append_line_basic", "test_read_lines_no_trailing_newline"],
    },
    {
        "id": "fileops-02",
        "instruction": "Fix `count_lines` so a trailing newline does not produce an extra phantom line "
        "count.",
        "difficulty": "easy",
        "category": "file-io",
        "lines": 1,
        "bug": ('return len(f.read().splitlines())', 'return len(f.read().split("\\n"))'),
        "fail_to_pass": ["test_count_lines_basic", "test_count_lines_empty"],
        "pass_to_pass": ["test_read_lines_basic", "test_tail_basic", "test_parse_kv_basic"],
    },
    {
        "id": "fileops-03",
        "instruction": "Fix `tail` so n=0 returns an empty list (the slice `[-0:]` currently returns the "
        "entire file).",
        "difficulty": "medium",
        "category": "file-io",
        "lines": 2,
        "bug": ("    if n <= 0:\n        return []\n    return lines[-n:]", "    return lines[-n:]"),
        "fail_to_pass": ["test_tail_zero", "test_tail_negative"],
        "pass_to_pass": ["test_read_lines_basic", "test_count_lines_basic", "test_append_line_basic", "test_tail_basic"],
    },
    {
        "id": "fileops-04",
        "instruction": "Fix `parse_kv` so a value containing '=' is preserved (split on the first '=' only, "
        "not every one).",
        "difficulty": "easy",
        "category": "file-io",
        "lines": 1,
        "bug": ('key, value = line.split("=", 1)', 'key, value = line.split("=")'),
        "fail_to_pass": ["test_parse_kv_value_with_equals", "test_parse_kv_multiple_equals"],
        "pass_to_pass": ["test_read_lines_basic", "test_tail_basic", "test_safe_write_creates_parent", "test_parse_kv_basic"],
    },
    {
        "id": "fileops-05",
        "instruction": "Fix `list_by_extension` so the extension match is case-insensitive (a .TXT file "
        "should match '.txt').",
        "difficulty": "easy",
        "category": "file-io",
        "lines": 1,
        "bug": (
            "return sorted(f for f in os.listdir(directory) if f.lower().endswith(extension.lower()))",
            "return sorted(f for f in os.listdir(directory) if f.endswith(extension))",
        ),
        "fail_to_pass": ["test_list_by_extension_case", "test_list_by_extension_upper_only"],
        "pass_to_pass": ["test_read_lines_basic", "test_tail_basic", "test_safe_write_creates_parent", "test_list_by_extension_empty"],
    },
    {
        "id": "fileops-06",
        "instruction": "Fix `safe_write` so it creates the parent directory of the target file before "
        "opening it (writing into a non-existent directory currently fails).",
        "difficulty": "medium",
        "category": "file-io",
        "lines": 2,
        "bug": (
            '    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)\n    with open(path, "w", encoding="utf-8") as f:',
            '    with open(path, "w", encoding="utf-8") as f:',
        ),
        "fail_to_pass": ["test_safe_write_creates_parent", "test_safe_write_deep_parent"],
        "pass_to_pass": ["test_read_lines_basic", "test_tail_basic", "test_append_line_basic", "test_safe_write_overwrites"],
    },
    {
        "id": "fileops-07",
        "instruction": "Fix `read_csv_as_dicts` so it skips the header row instead of turning it into a "
        "data record.",
        "difficulty": "medium",
        "category": "file-io",
        "lines": 1,
        "bug": ("return [dict(zip(header, row)) for row in rows[1:]]", "return [dict(zip(header, row)) for row in rows]"),
        "fail_to_pass": ["test_read_csv_as_dicts_skips_header", "test_read_csv_as_dicts_basic"],
        "pass_to_pass": ["test_read_lines_basic", "test_count_lines_basic", "test_parse_kv_basic"],
    },
    {
        "id": "fileops-08",
        "instruction": "Fix `append_line` so it writes a trailing newline after each line (successive "
        "appends currently concatenate onto one line).",
        "difficulty": "easy",
        "category": "file-io",
        "lines": 1,
        "bug": ('        f.write(line + "\\n")', "        f.write(line)"),
        "fail_to_pass": ["test_append_line_basic", "test_append_line_creates_file"],
        "pass_to_pass": ["test_read_lines_basic", "test_tail_basic", "test_count_lines_basic"],
    },
]

# --------------------------------------------------------------------------- #
# ds — data structures
# --------------------------------------------------------------------------- #

DS_MODULE = '''"""Small data-structure library (intentionally buggy for eval tasks)."""


class Node:
    def __init__(self, value):
        self.value = value
        self.next = None


class TreeNode:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None


def linked_list_len(head):
    """Return the number of nodes in a linked list."""
    count = 0
    while head is not None:
        count += 1
        head = head.next
    return count


def linked_list_append(head, value):
    """Append ``value`` to the end of a linked list and return the head."""
    new = Node(value)
    if head is None:
        return new
    cur = head
    while cur.next is not None:
        cur = cur.next
    cur.next = new
    return head


def linked_list_reverse(head):
    """Reverse a linked list in place and return the new head."""
    prev = None
    cur = head
    while cur is not None:
        nxt = cur.next
        cur.next = prev
        prev = cur
        cur = nxt
    return prev


def stack_push(stack, value):
    """Push ``value`` onto ``stack`` (a list) and return the stack."""
    stack.append(value)
    return stack


def stack_pop(stack):
    """Pop the top of ``stack``, raising IndexError when empty."""
    if not stack:
        raise IndexError("pop from empty stack")
    return stack.pop()


def stack_peek(stack):
    """Return the top of ``stack`` without removing it, raising IndexError when empty."""
    if not stack:
        raise IndexError("peek from empty stack")
    return stack[-1]


class RingBuffer:
    def __init__(self, capacity):
        self.capacity = capacity
        self.buf = [None] * capacity
        self.head = 0
        self.size = 0

    def push(self, value):
        tail = (self.head + self.size) % self.capacity
        self.buf[tail] = value
        if self.size < self.capacity:
            self.size += 1
        else:
            self.head = (self.head + 1) % self.capacity

    def to_list(self):
        return [self.buf[(self.head + i) % self.capacity] for i in range(self.size)]


class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self._items = {}
        self._order = []

    def get(self, key):
        if key not in self._items:
            return -1
        self._order.remove(key)
        self._order.append(key)
        return self._items[key]

    def put(self, key, value):
        if key in self._items:
            self._order.remove(key)
        self._items[key] = value
        self._order.append(key)
        if len(self._items) > self.capacity:
            evict = self._order.pop(0)
            del self._items[evict]


def binary_tree_height(root):
    """Return the height of a binary tree (0 for an empty tree)."""
    if root is None:
        return 0
    return 1 + max(binary_tree_height(root.left), binary_tree_height(root.right))
'''

DS_TESTS = '''import pytest

import ds


def _ll(values):
    head = None
    tail = None
    for v in values:
        node = ds.Node(v)
        if head is None:
            head = node
        else:
            tail.next = node
        tail = node
    return head


def _values(head):
    out = []
    while head is not None:
        out.append(head.value)
        head = head.next
    return out


def test_linked_list_len_basic():
    assert ds.linked_list_len(_ll([1, 2, 3])) == 3


def test_linked_list_len_empty():
    assert ds.linked_list_len(None) == 0


def test_linked_list_append_build():
    assert _values(ds.linked_list_append(_ll([1, 2]), 3)) == [1, 2, 3]


def test_linked_list_append_single():
    assert _values(ds.linked_list_append(_ll([1]), 5)) == [1, 5]


def test_linked_list_append_empty():
    head = ds.linked_list_append(None, 5)
    assert head is not None and head.value == 5


def test_linked_list_reverse_basic():
    assert _values(ds.linked_list_reverse(_ll([1, 2, 3]))) == [3, 2, 1]


def test_linked_list_reverse_single():
    head = ds.linked_list_reverse(_ll([1]))
    assert head.value == 1 and head.next is None


def test_stack_push_pop():
    s = []
    ds.stack_push(s, 1)
    ds.stack_push(s, 2)
    assert ds.stack_pop(s) == 2
    assert ds.stack_pop(s) == 1


def test_stack_pop_empty_raises():
    with pytest.raises(IndexError):
        ds.stack_pop([])


def test_stack_pop_empty_message():
    with pytest.raises(IndexError, match="empty"):
        ds.stack_pop([])


def test_stack_peek_basic():
    assert ds.stack_peek([1, 2, 3]) == 3


def test_stack_peek_two():
    assert ds.stack_peek([5, 8]) == 8


def test_stack_peek_empty_raises():
    with pytest.raises(IndexError):
        ds.stack_peek([])


def test_ring_buffer_wraparound():
    rb = ds.RingBuffer(3)
    for v in [1, 2, 3, 4, 5]:
        rb.push(v)
    assert rb.to_list() == [3, 4, 5]


def test_ring_buffer_exact_full():
    rb = ds.RingBuffer(3)
    for v in [1, 2, 3, 4]:
        rb.push(v)
    assert rb.to_list() == [2, 3, 4]


def test_ring_buffer_partial():
    rb = ds.RingBuffer(3)
    rb.push(1)
    rb.push(2)
    assert rb.to_list() == [1, 2]


def test_lru_get_missing():
    assert ds.LRUCache(2).get("x") == -1


def test_lru_get_updates_recency():
    cache = ds.LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")
    cache.put("c", 3)
    assert cache.get("a") == 1
    assert cache.get("b") == -1


def test_lru_get_refreshes_after_eviction():
    cache = ds.LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    cache.get("b")
    cache.put("d", 4)
    assert cache.get("b") == 2
    assert cache.get("c") == -1


def test_lru_put_evicts_least_recent():
    cache = ds.LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    assert cache.get("a") == -1
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_lru_put_capacity_one():
    cache = ds.LRUCache(1)
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == -1
    assert cache.get("b") == 2


def test_lru_put_updates_existing():
    cache = ds.LRUCache(2)
    cache.put("a", 1)
    cache.put("a", 99)
    assert cache.get("a") == 99


def test_binary_tree_height_basic():
    root = ds.TreeNode(1)
    root.left = ds.TreeNode(2)
    root.left.left = ds.TreeNode(3)
    assert ds.binary_tree_height(root) == 3


def test_binary_tree_height_single():
    root = ds.TreeNode(1)
    assert ds.binary_tree_height(root) == 1


def test_binary_tree_height_empty():
    assert ds.binary_tree_height(None) == 0
'''

DS_TASKS = [
    {
        "id": "ds-01",
        "instruction": "Fix `linked_list_len` so it counts the final node (the loop currently stops one "
        "node early).",
        "difficulty": "easy",
        "category": "data-structure",
        "lines": 1,
        "bug": ("    while head is not None:", "    while head.next is not None:"),
        "fail_to_pass": ["test_linked_list_len_basic", "test_linked_list_len_empty"],
        "pass_to_pass": ["test_stack_push_pop", "test_linked_list_reverse_single"],
    },
    {
        "id": "ds-02",
        "instruction": "Fix `linked_list_append` so it walks only as far as the last node (the current "
        "loop walks past the tail and crashes).",
        "difficulty": "medium",
        "category": "data-structure",
        "lines": 1,
        "bug": ("    while cur.next is not None:", "    while cur is not None:"),
        "fail_to_pass": ["test_linked_list_append_build", "test_linked_list_append_single"],
        "pass_to_pass": ["test_linked_list_len_basic", "test_stack_peek_basic", "test_linked_list_append_empty"],
    },
    {
        "id": "ds-03",
        "instruction": "Fix `linked_list_reverse` so it returns the new head (the current version returns "
        "the stale tail pointer).",
        "difficulty": "medium",
        "category": "data-structure",
        "lines": 1,
        "bug": ("    return prev", "    return cur"),
        "fail_to_pass": ["test_linked_list_reverse_basic", "test_linked_list_reverse_single"],
        "pass_to_pass": ["test_linked_list_len_basic", "test_stack_push_pop"],
    },
    {
        "id": "ds-04",
        "instruction": "Fix `stack_pop` so it raises `IndexError` on an empty stack instead of silently "
        "returning None.",
        "difficulty": "easy",
        "category": "data-structure",
        "lines": 2,
        "bug": (
            '    if not stack:\n        raise IndexError("pop from empty stack")\n    return stack.pop()',
            "    if not stack:\n        return None\n    return stack.pop()",
        ),
        "fail_to_pass": ["test_stack_pop_empty_raises", "test_stack_pop_empty_message"],
        "pass_to_pass": ["test_linked_list_len_basic", "test_linked_list_reverse_single", "test_stack_push_pop"],
    },
    {
        "id": "ds-05",
        "instruction": "Fix `stack_peek` so it returns the top element (the last one) instead of the "
        "bottom.",
        "difficulty": "easy",
        "category": "data-structure",
        "lines": 1,
        "bug": ("    return stack[-1]", "    return stack[0]"),
        "fail_to_pass": ["test_stack_peek_basic", "test_stack_peek_two"],
        "pass_to_pass": ["test_linked_list_len_basic", "test_stack_push_pop", "test_stack_peek_empty_raises"],
    },
    {
        "id": "ds-06",
        "instruction": "Fix `RingBuffer.push` so the tail index wraps with modulo once the buffer is full "
        "(the current code indexes past the end of the backing array).",
        "difficulty": "hard",
        "category": "data-structure",
        "lines": 1,
        "bug": ("tail = (self.head + self.size) % self.capacity", "tail = self.head + self.size"),
        "fail_to_pass": ["test_ring_buffer_wraparound", "test_ring_buffer_exact_full"],
        "pass_to_pass": ["test_stack_push_pop", "test_linked_list_len_basic", "test_ring_buffer_partial"],
    },
    {
        "id": "ds-07",
        "instruction": "Fix `LRUCache.get` so it refreshes the accessed key's recency (the current code "
        "returns the value but does not move the key to most-recently-used).",
        "difficulty": "medium",
        "category": "data-structure",
        "lines": 3,
        "bug": (
            "        self._order.remove(key)\n        self._order.append(key)\n        return self._items[key]",
            "        return self._items[key]",
        ),
        "fail_to_pass": ["test_lru_get_updates_recency", "test_lru_get_refreshes_after_eviction"],
        "pass_to_pass": ["test_stack_push_pop", "test_linked_list_len_basic", "test_binary_tree_height_basic", "test_lru_get_missing"],
    },
    {
        "id": "ds-08",
        "instruction": "Fix `LRUCache.put` so it evicts the least-recently-used key (the current code pops "
        "the most-recently-used key instead).",
        "difficulty": "hard",
        "category": "data-structure",
        "lines": 1,
        "bug": ("            evict = self._order.pop(0)", "            evict = self._order.pop()"),
        "fail_to_pass": ["test_lru_put_evicts_least_recent", "test_lru_put_capacity_one"],
        "pass_to_pass": ["test_stack_push_pop", "test_linked_list_len_basic", "test_binary_tree_height_basic", "test_lru_put_updates_existing"],
    },
    {
        "id": "ds-09",
        "instruction": "Fix `binary_tree_height` so a single-node tree has height 1 (the current code "
        "under-counts by one because it drops the leading 1).",
        "difficulty": "easy",
        "category": "data-structure",
        "lines": 1,
        "bug": ("    return 1 + max(binary_tree_height(root.left), binary_tree_height(root.right))", "    return max(binary_tree_height(root.left), binary_tree_height(root.right))"),
        "fail_to_pass": ["test_binary_tree_height_basic", "test_binary_tree_height_single"],
        "pass_to_pass": ["test_stack_push_pop", "test_linked_list_len_basic", "test_binary_tree_height_empty"],
    },
]

# --------------------------------------------------------------------------- #
# codec — encoding / decoding utilities
# --------------------------------------------------------------------------- #

CODEC_MODULE = '''"""Small encoding/decoding utilities (intentionally buggy for eval tasks)."""

import base64
import unicodedata
from urllib.parse import quote, unquote, unquote_plus


def base64_encode(data):
    """Base64-encode a string and return the ASCII text."""
    return base64.b64encode(data.encode("utf-8")).decode("ascii")


def base64_decode(text):
    """Base64-decode ASCII text back into a UTF-8 string."""
    return base64.b64decode(text).decode("utf-8")


def hex_encode(data):
    """Hex-encode a string."""
    return data.encode("utf-8").hex()


def hex_decode(text):
    """Decode a hex string back into a UTF-8 string."""
    return bytes.fromhex(text).decode("utf-8")


def url_encode(text):
    """Percent-encode ``text`` (encoding spaces and reserved characters)."""
    return quote(text, safe="")


def url_decode(text):
    """Decode a percent-encoded (form) string, turning '+' into space."""
    return unquote_plus(text)


def char_count(text):
    """Return the number of characters in ``text``."""
    return len(text)


def byte_count(text):
    """Return the number of UTF-8 bytes in ``text``."""
    return len(text.encode("utf-8"))


def normalize(text):
    """Return the NFC-normalised form of ``text``."""
    return unicodedata.normalize("NFC", text)
'''

CODEC_TESTS = '''import codec


def test_base64_encode_basic():
    assert codec.base64_encode("hello") == "aGVsbG8="


def test_base64_encode_roundtrip():
    assert codec.base64_decode(codec.base64_encode("hello world")) == "hello world"


def test_base64_decode_basic():
    assert codec.base64_decode("aGVsbG8=") == "hello"


def test_hex_encode_basic():
    assert codec.hex_encode("AB") == "4142"


def test_hex_decode_basic():
    assert codec.hex_decode("4142") == "AB"


def test_hex_roundtrip_unicode():
    assert codec.hex_decode(codec.hex_encode("\\u4e2d")) == "\\u4e2d"


def test_url_encode_spaces():
    assert codec.url_encode("hello world") == "hello%20world"


def test_url_encode_reserved():
    assert codec.url_encode("a/b") == "a%2Fb"


def test_url_encode_multiple_slashes():
    assert codec.url_encode("a/b/c") == "a%2Fb%2Fc"


def test_url_decode_plus():
    assert codec.url_decode("hello+world") == "hello world"


def test_url_decode_plus_multiple():
    assert codec.url_decode("a+b+c") == "a b c"


def test_url_decode_percent():
    assert codec.url_decode("hello%20world") == "hello world"


def test_char_count_ascii():
    assert codec.char_count("hello") == 5


def test_char_count_unicode():
    assert codec.char_count("\\u4e2d\\u6587") == 2


def test_byte_count_ascii():
    assert codec.byte_count("hello") == 5


def test_byte_count_unicode():
    assert codec.byte_count("\\u4e2d") == 3


def test_byte_count_unicode_two():
    assert codec.byte_count("\\u4e2d\\u6587") == 6


def test_normalize_composed():
    assert codec.normalize("e\\u0301") == "\\u00e9"


def test_normalize_composed_two():
    assert codec.normalize("a\\u0300") == "\\u00e0"


def test_normalize_already_nfc():
    assert codec.normalize("hello") == "hello"
'''

CODEC_TASKS = [
    {
        "id": "codec-01",
        "instruction": "Fix `base64_encode` so it encodes the string's UTF-8 bytes (the current code "
        "passes the raw str, which base64 rejects).",
        "difficulty": "easy",
        "category": "encoding",
        "lines": 1,
        "bug": ('base64.b64encode(data.encode("utf-8")).decode("ascii")', "base64.b64encode(data)"),
        "fail_to_pass": ["test_base64_encode_basic", "test_base64_encode_roundtrip"],
        "pass_to_pass": ["test_hex_encode_basic", "test_char_count_ascii", "test_url_encode_spaces"],
    },
    {
        "id": "codec-02",
        "instruction": "Fix `base64_decode` so it decodes the bytes back to a UTF-8 string (the current "
        "code returns raw bytes).",
        "difficulty": "easy",
        "category": "encoding",
        "lines": 1,
        "bug": ('return base64.b64decode(text).decode("utf-8")', "return base64.b64decode(text)"),
        "fail_to_pass": ["test_base64_decode_basic", "test_base64_encode_roundtrip"],
        "pass_to_pass": ["test_hex_decode_basic", "test_char_count_ascii", "test_url_decode_percent"],
    },
    {
        "id": "codec-03",
        "instruction": "Fix `hex_encode` so it encodes the string's UTF-8 bytes (the current code calls "
        "`.hex()` directly on the str, which has no such method).",
        "difficulty": "easy",
        "category": "encoding",
        "lines": 1,
        "bug": ('return data.encode("utf-8").hex()', "return data.hex()"),
        "fail_to_pass": ["test_hex_encode_basic", "test_hex_roundtrip_unicode"],
        "pass_to_pass": ["test_base64_encode_basic", "test_char_count_ascii", "test_url_encode_spaces"],
    },
    {
        "id": "codec-04",
        "instruction": "Fix `hex_decode` so it decodes the bytes back to a UTF-8 string (the current code "
        "returns raw bytes).",
        "difficulty": "easy",
        "category": "encoding",
        "lines": 1,
        "bug": ('return bytes.fromhex(text).decode("utf-8")', "return bytes.fromhex(text)"),
        "fail_to_pass": ["test_hex_decode_basic", "test_hex_roundtrip_unicode"],
        "pass_to_pass": ["test_base64_decode_basic", "test_char_count_ascii", "test_url_decode_percent"],
    },
    {
        "id": "codec-05",
        "instruction": "Fix `url_encode` so it percent-encodes reserved characters such as '/' (the "
        "current code passes '/' through unencoded).",
        "difficulty": "medium",
        "category": "encoding",
        "lines": 1,
        "bug": ('return quote(text, safe="")', "return quote(text)"),
        "fail_to_pass": ["test_url_encode_reserved", "test_url_encode_multiple_slashes"],
        "pass_to_pass": ["test_base64_encode_basic", "test_char_count_ascii", "test_hex_encode_basic", "test_url_encode_spaces"],
    },
    {
        "id": "codec-06",
        "instruction": "Fix `url_decode` so it treats '+' as a space (application/x-www-form-urlencoded); "
        "the current code leaves '+' untouched.",
        "difficulty": "medium",
        "category": "encoding",
        "lines": 1,
        "bug": ("return unquote_plus(text)", "return unquote(text)"),
        "fail_to_pass": ["test_url_decode_plus", "test_url_decode_plus_multiple"],
        "pass_to_pass": ["test_base64_decode_basic", "test_char_count_ascii", "test_hex_decode_basic", "test_url_decode_percent"],
    },
    {
        "id": "codec-07",
        "instruction": "Fix `byte_count` so it returns the UTF-8 byte length (the current code returns the "
        "character count, which is wrong for multi-byte characters).",
        "difficulty": "medium",
        "category": "encoding",
        "lines": 1,
        "bug": ('return len(text.encode("utf-8"))', "return len(text)"),
        "fail_to_pass": ["test_byte_count_unicode", "test_byte_count_unicode_two"],
        "pass_to_pass": ["test_char_count_ascii", "test_char_count_unicode", "test_hex_encode_basic", "test_byte_count_ascii"],
    },
    {
        "id": "codec-08",
        "instruction": "Fix `normalize` so it returns the NFC-normalised form (the current code returns "
        "the input unchanged, so decomposed forms are not composed).",
        "difficulty": "hard",
        "category": "encoding",
        "lines": 1,
        "bug": ('return unicodedata.normalize("NFC", text)', "return text"),
        "fail_to_pass": ["test_normalize_composed", "test_normalize_composed_two"],
        "pass_to_pass": ["test_char_count_ascii", "test_hex_encode_basic", "test_base64_encode_basic", "test_normalize_already_nfc"],
    },
]

# --------------------------------------------------------------------------- #
# parselib — text/config parsing with robust error handling
# --------------------------------------------------------------------------- #

PARSELIB_MODULE = '''"""Small text/config parsing utilities (intentionally buggy for eval tasks)."""

import csv
import io
import json


def parse_json(text):
    """Parse a JSON string, treating blank input as an empty dict."""
    if not text.strip():
        return {}
    return json.loads(text)


def strip_comments(text):
    """Remove `#` line comments from a text block."""
    out = []
    for line in text.splitlines():
        out.append(line.split("#", 1)[0].rstrip())
    return "\\n".join(out)


def parse_csv(text):
    """Parse a CSV string into a list of rows (honouring quoted fields)."""
    return [row for row in csv.reader(io.StringIO(text))]


def parse_kv(text):
    """Parse 'key=value' lines into a dict (last occurrence of a key wins)."""
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def parse_ini(text):
    """Parse an INI-style text into nested dicts by [section]."""
    result = {}
    current = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            result[current] = {}
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if current is not None:
            result[current][key.strip()] = value.strip()
        else:
            result[key.strip()] = value.strip()
    return result


def sum_column(rows, idx):
    """Sum the numeric values in column ``idx`` of ``rows``."""
    total = 0.0
    for row in rows:
        total += float(row[idx])
    return total


def get_field(record, key, default=None):
    """Return ``record[key]`` or ``default`` when the key is missing."""
    return record.get(key, default)


def split_words(text):
    """Split ``text`` on whitespace into words."""
    return text.split()
'''

PARSELIB_TESTS = '''import parselib


def test_parse_json_blank():
    assert parselib.parse_json("   ") == {}


def test_parse_json_empty():
    assert parselib.parse_json("") == {}


def test_parse_json_object():
    assert parselib.parse_json('{"a": 1}') == {"a": 1}


def test_strip_comments_basic():
    assert parselib.strip_comments("a = 1  # inline\\nb = 2\\n") == "a = 1\\nb = 2"


def test_strip_comments_full_line():
    assert parselib.strip_comments("# full comment\\ncode\\n") == "\\ncode"


def test_strip_comments_no_comment():
    assert parselib.strip_comments("plain\\ntext\\n") == "plain\\ntext"


def test_parse_csv_quoted_field():
    assert parselib.parse_csv('a,"b,c",d\\n') == [["a", "b,c", "d"]]


def test_parse_csv_quoted_two():
    assert parselib.parse_csv('"x,y","z,w"\\n') == [["x,y", "z,w"]]


def test_parse_csv_basic():
    assert parselib.parse_csv("x,y\\n1,2\\n") == [["x", "y"], ["1", "2"]]


def test_parse_kv_value_with_equals():
    assert parselib.parse_kv("url=https://a.com?x=1\\n") == {"url": "https://a.com?x=1"}


def test_parse_kv_multiple_equals():
    assert parselib.parse_kv("a=b=c\\n") == {"a": "b=c"}


def test_parse_kv_basic():
    assert parselib.parse_kv("name=alice\\nage=30\\n") == {"name": "alice", "age": "30"}


def test_parse_ini_top_level():
    text = "title=My App\\n[server]\\nhost=localhost\\n"
    assert parselib.parse_ini(text)["title"] == "My App"


def test_parse_ini_top_level_only():
    assert parselib.parse_ini("title=My App\\n") == {"title": "My App"}


def test_parse_ini_sections():
    text = "[server]\\nhost=localhost\\n[db]\\nport=5432\\n"
    assert parselib.parse_ini(text) == {"server": {"host": "localhost"}, "db": {"port": "5432"}}


def test_sum_column_floats():
    assert parselib.sum_column([["1.5"], ["2.5"]], 0) == 4.0


def test_sum_column_mixed():
    assert parselib.sum_column([["1"], ["2.5"]], 0) == 3.5


def test_sum_column_basic():
    assert parselib.sum_column([["1", "2"], ["3", "4"]], 0) == 4.0


def test_get_field_missing():
    assert parselib.get_field({}, "x") is None


def test_get_field_missing_default():
    assert parselib.get_field({"a": 1}, "b", default=0) == 0


def test_get_field_present():
    assert parselib.get_field({"a": 1}, "a") == 1


def test_split_words_multiple_spaces():
    assert parselib.split_words("a  b\\tc") == ["a", "b", "c"]


def test_split_words_leading():
    assert parselib.split_words("  a  b  ") == ["a", "b"]


def test_split_words_basic():
    assert parselib.split_words("hello world") == ["hello", "world"]
'''

PARSELIB_TASKS = [
    {
        "id": "parselib-01",
        "instruction": "Fix `parse_json` so blank input parses to an empty dict instead of raising a JSON "
        "decode error.",
        "difficulty": "easy",
        "category": "parsing",
        "lines": 2,
        "bug": (
            "    if not text.strip():\n        return {}\n    return json.loads(text)",
            "    return json.loads(text)",
        ),
        "fail_to_pass": ["test_parse_json_blank", "test_parse_json_empty"],
        "pass_to_pass": ["test_parse_csv_basic", "test_parse_kv_basic", "test_get_field_present", "test_parse_json_object"],
    },
    {
        "id": "parselib-02",
        "instruction": "Fix `strip_comments` so it keeps the code before a `#` comment (the current code "
        "keeps the comment text instead of the code).",
        "difficulty": "medium",
        "category": "parsing",
        "lines": 1,
        "bug": ('out.append(line.split("#", 1)[0].rstrip())', 'out.append(line.split("#", 1)[-1].rstrip())'),
        "fail_to_pass": ["test_strip_comments_basic", "test_strip_comments_full_line"],
        "pass_to_pass": ["test_parse_json_object", "test_split_words_basic", "test_get_field_present", "test_strip_comments_no_comment"],
    },
    {
        "id": "parselib-03",
        "instruction": "Fix `parse_csv` so quoted fields containing commas are kept as a single field (the "
        "current code splits on every comma).",
        "difficulty": "hard",
        "category": "parsing",
        "lines": 1,
        "bug": ("return [row for row in csv.reader(io.StringIO(text))]", "return [line.split(\",\") for line in text.splitlines()]"),
        "fail_to_pass": ["test_parse_csv_quoted_field", "test_parse_csv_quoted_two"],
        "pass_to_pass": ["test_parse_json_object", "test_parse_kv_basic", "test_get_field_present", "test_parse_csv_basic"],
    },
    {
        "id": "parselib-04",
        "instruction": "Fix `parse_kv` so a value containing '=' is preserved (split on the first '=' "
        "only).",
        "difficulty": "medium",
        "category": "parsing",
        "lines": 1,
        "bug": (
            'key, value = line.split("=", 1)\n        result[key.strip()] = value.strip()',
            'key, value = line.split("=")\n        result[key.strip()] = value.strip()',
        ),
        "fail_to_pass": ["test_parse_kv_value_with_equals", "test_parse_kv_multiple_equals"],
        "pass_to_pass": ["test_parse_json_object", "test_parse_csv_basic", "test_sum_column_basic", "test_parse_kv_basic"],
    },
    {
        "id": "parselib-05",
        "instruction": "Fix `parse_ini` so keys appearing before any [section] are retained (the current "
        "code silently drops them).",
        "difficulty": "hard",
        "category": "parsing",
        "lines": 3,
        "bug": (
            "        if current is not None:\n            result[current][key.strip()] = value.strip()\n        else:\n            result[key.strip()] = value.strip()",
            "        if current is not None:\n            result[current][key.strip()] = value.strip()",
        ),
        "fail_to_pass": ["test_parse_ini_top_level", "test_parse_ini_top_level_only"],
        "pass_to_pass": ["test_parse_json_object", "test_parse_kv_basic", "test_get_field_present", "test_parse_ini_sections"],
    },
    {
        "id": "parselib-06",
        "instruction": "Fix `sum_column` so it sums floats (the current code coerces with int() and "
        "crashes on decimals).",
        "difficulty": "easy",
        "category": "parsing",
        "lines": 1,
        "bug": ("        total += float(row[idx])", "        total += int(row[idx])"),
        "fail_to_pass": ["test_sum_column_floats", "test_sum_column_mixed"],
        "pass_to_pass": ["test_parse_json_object", "test_get_field_present", "test_split_words_basic", "test_sum_column_basic"],
    },
    {
        "id": "parselib-07",
        "instruction": "Fix `get_field` so a missing key returns the default instead of raising KeyError.",
        "difficulty": "easy",
        "category": "exception",
        "lines": 1,
        "bug": ("return record.get(key, default)", "return record[key]"),
        "fail_to_pass": ["test_get_field_missing", "test_get_field_missing_default"],
        "pass_to_pass": ["test_parse_json_object", "test_split_words_basic", "test_parse_csv_basic", "test_get_field_present"],
    },
    {
        "id": "parselib-08",
        "instruction": "Fix `split_words` so it splits on any whitespace run (the current code splits on a "
        "single space, leaving empty tokens for multiple spaces).",
        "difficulty": "easy",
        "category": "string",
        "lines": 1,
        "bug": ("return text.split()", 'return text.split(" ")'),
        "fail_to_pass": ["test_split_words_multiple_spaces", "test_split_words_leading"],
        "pass_to_pass": ["test_parse_json_object", "test_get_field_present", "test_parse_csv_basic", "test_split_words_basic"],
    },
]

# --------------------------------------------------------------------------- #

REPOS = {
    "textutils": {"module": TEXTUTILS_MODULE, "tests": TEXTUTILS_TESTS, "tasks": TEXTUTILS_TASKS},
    "numstats": {"module": NUMSTATS_MODULE, "tests": NUMSTATS_TESTS, "tasks": NUMSTATS_TASKS},
    "rpncalc": {"module": RPNCALC_MODULE, "tests": RPNCALC_TESTS, "tasks": RPNCALC_TASKS},
    "datastore": {"module": DATASTORE_MODULE, "tests": DATASTORE_TESTS, "tasks": DATASTORE_TASKS},
    "seqops": {"module": SEQOPS_MODULE, "tests": SEQOPS_TESTS, "tasks": SEQOPS_TASKS},
    "fileops": {"module": FILEOPS_MODULE, "tests": FILEOPS_TESTS, "tasks": FILEOPS_TASKS},
    "ds": {"module": DS_MODULE, "tests": DS_TESTS, "tasks": DS_TASKS},
    "codec": {"module": CODEC_MODULE, "tests": CODEC_TESTS, "tasks": CODEC_TASKS},
    "parselib": {"module": PARSELIB_MODULE, "tests": PARSELIB_TESTS, "tasks": PARSELIB_TASKS},
}


def build() -> list[Task]:
    """Materialise all repos + task JSONs. Returns the list of Task objects."""
    tasks: list[Task] = []
    for repo, spec in REPOS.items():
        module = spec["module"]
        for t in spec["tasks"]:
            buggy = apply_fix(module, t["bug"][0], t["bug"][1])
            patch = make_patch(buggy, module, f"{repo}.py")
            if not patch:
                raise ValueError(f"empty gold_patch for {t['id']}")

            task_dir = REPOS_DIR / repo / t["id"]
            write_text(task_dir / f"{repo}.py", buggy)
            write_text(task_dir / "conftest.py", CONFTEST)
            write_text(task_dir / "tests" / f"test_{repo}.py", spec["tests"])

            task = Task(
                id=t["id"],
                repo=repo,
                instruction=t["instruction"],
                gold_patch=patch,
                repo_path=f"tasks/repos/{repo}/{t['id']}",
                fail_to_pass=[f"tests/test_{repo}.py::{name}" for name in t["fail_to_pass"]],
                pass_to_pass=[f"tests/test_{repo}.py::{name}" for name in t["pass_to_pass"]],
                metadata={
                    "difficulty": t["difficulty"],
                    "category": t["category"],
                    "estimated_lines": t["lines"],
                },
            )
            write_text(TASKS_DIR / f"{t['id']}.json", json.dumps(task.model_dump(), indent=2, ensure_ascii=False) + "\n")
            tasks.append(task)
    return tasks


def verify(tasks: list[Task]) -> int:
    """Double-directionally verify every task. Returns number of failures."""
    failures = 0
    for task in tasks:
        result = verify_gold_patch(task)
        if result.ok:
            print(f"OK   {task.id}")
        else:
            failures += 1
            print(f"FAIL {task.id}: {result.failures}")
    print(f"\n{len(tasks) - failures}/{len(tasks)} tasks verified double-directionally")
    return failures


def main() -> int:
    # Clean slate: rebuild every task JSON and every repo directory.
    for f in TASKS_DIR.glob("*.json"):
        f.unlink()
    for child in REPOS_DIR.iterdir():
        if child.is_dir():
            shutil.rmtree(child)

    tasks = build()
    print(f"built {len(tasks)} tasks across {len(REPOS)} repos")
    return verify(tasks)


if __name__ == "__main__":
    sys.exit(main())
