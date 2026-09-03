"""INI-style config parsing with ``[section]`` headers and top-level keys."""

from parselib.textutil import parse_kv


def parse_ini(text: str) -> dict:
    """Parse INI ``text`` into a nested dict.

    Lines before the first ``[section]`` header are collected as top-level keys.
    Each ``[section]`` begins a nested dict; repeated section headers merge into
    the same dict. ``key = value`` pairs use the same syntax as
    :func:`parselib.textutil.parse_kv`. Blank lines and ``#``/``;`` comments are
    ignored.
    """
    result: dict = {}
    section = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#",)):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            result.setdefault(section, {})
            continue
        pair = parse_kv(line)
        if pair is None:
            continue
        key, value = pair
        target = result if section is None else result[section]
        target[key] = value
    return result
