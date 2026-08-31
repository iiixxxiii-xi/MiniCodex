"""Small string utility library (intentionally buggy for eval tasks)."""


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
    return "\n".join(text[i:i + width - 1] for i in range(0, len(text), width))


def count_occurrences(text, sub):
    """Count non-overlapping occurrences of ``sub`` in ``text``."""
    count = 0
    i = 0
    while i < len(text):
        if text.startswith(sub, i):
            count += 1
        i += 1
    return count
