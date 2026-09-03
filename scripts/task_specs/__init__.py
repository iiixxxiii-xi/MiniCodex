"""Repo-level task specifications.

Each sibling module describes ONE repo (a multi-module package) and defines the
four attributes the builder reads:

  * ``REPO``  — package/repo name (``str``).
  * ``FILES`` — ``{relative_path: correct_source}`` for every source file.
  * ``TESTS`` — ``{relative_path: test_source}`` for every test file.
  * ``TASKS`` — a list of task dicts; each task injects one realistic bug via a
    ``bug`` list of ``(path, correct_snippet, buggy_snippet)`` edits (the bug may
    span modules) and carries ``fail_to_pass`` / ``pass_to_pass`` as full pytest
    node ids (e.g. ``"tests/test_binary.py::test_roundtrip"``).

Modules are auto-discovered by ``build_tasks.py``; this package's ``__init__`` is
intentionally empty.
"""
