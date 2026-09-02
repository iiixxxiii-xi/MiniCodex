"""Verification logic: FAIL_TO_PASS + PASS_TO_PASS (SWE-bench style).

These tests exercise the two entry points the harness relies on:

* ``verify_workspace`` — the runner's PASS/FAIL verdict for a patched
  workspace: every ``fail_to_pass`` AND every ``pass_to_pass`` test must pass.
* ``verify_gold_patch`` — the build-time double-directional check: on the buggy
  baseline every ``fail_to_pass`` test fails and every ``pass_to_pass`` test
  passes; after applying ``gold_patch`` everything passes.
"""

import difflib

from minicodex.eval.task import Task
from minicodex.eval.verification import GoldVerification, verify_gold_patch, verify_workspace

CONFTEST = "import os\nimport sys\n\nsys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"


def _make_patch(buggy: str, fixed: str, filename: str = "demo.py") -> str:
    diff = list(
        difflib.unified_diff(
            buggy.splitlines(keepends=True),
            fixed.splitlines(keepends=True),
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        )
    )
    return f"diff --git a/{filename} b/{filename}\n" + "".join(diff)


def _write_repo(root, module_src: str, test_src: str) -> None:
    (root / "demo.py").write_text(module_src, encoding="utf-8")
    (root / "conftest.py").write_text(CONFTEST, encoding="utf-8")
    tests = root / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    (tests / "test_demo.py").write_text(test_src, encoding="utf-8")


GOOD_MODULE = "def add(a, b):\n    return a + b\n\n\ndef mul(a, b):\n    return a * b\n"
BUGGY_MODULE = "def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n"
TESTS = "import demo\n\n\ndef test_add():\n    assert demo.add(2, 3) == 5\n\n\ndef test_mul():\n    assert demo.mul(2, 3) == 6\n"
ADD_NODE = "tests/test_demo.py::test_add"
MUL_NODE = "tests/test_demo.py::test_mul"


def _task(workspace, **overrides) -> Task:
    kwargs = dict(
        id="t1",
        repo="demo",
        instruction="fix add",
        repo_path=str(workspace),
        fail_to_pass=[ADD_NODE],
        pass_to_pass=[MUL_NODE],
    )
    kwargs.update(overrides)
    return Task(**kwargs)


def test_verify_workspace_passes_when_all_tests_pass(tmp_path):
    _write_repo(tmp_path, GOOD_MODULE, TESTS)
    passed, error, _ = verify_workspace(_task(tmp_path), tmp_path)
    assert passed is True
    assert error == ""


def test_verify_workspace_fails_when_fail_to_pass_broken(tmp_path):
    # add is broken -> fail_to_pass test_add fails.
    _write_repo(tmp_path, BUGGY_MODULE, TESTS)
    passed, error, _ = verify_workspace(_task(tmp_path), tmp_path)
    assert passed is False
    assert "fail_to_pass" in error


def test_verify_workspace_fails_on_pass_to_pass_regression(tmp_path):
    # The "fixed correctly but broke a regression test" scenario: add is fixed,
    # but mul is now broken, so pass_to_pass fails -> overall FAIL.
    module = "def add(a, b):\n    return a + b\n\n\ndef mul(a, b):\n    return a + b\n"
    _write_repo(tmp_path, module, TESTS)
    passed, error, _ = verify_workspace(_task(tmp_path), tmp_path)
    assert passed is False
    assert "pass_to_pass" in error


def test_verify_workspace_fails_when_both_broken(tmp_path):
    module = "def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a + b\n"
    _write_repo(tmp_path, module, TESTS)
    passed, error, _ = verify_workspace(_task(tmp_path), tmp_path)
    assert passed is False
    assert "fail_to_pass" in error
    assert "pass_to_pass" in error


def test_verify_gold_patch_ok_double_directional(tmp_path):
    _write_repo(tmp_path, BUGGY_MODULE, TESTS)
    task = _task(
        tmp_path,
        gold_patch=_make_patch(BUGGY_MODULE, GOOD_MODULE),
    )
    result = verify_gold_patch(task)
    assert isinstance(result, GoldVerification)
    assert result.ok is True, result.failures
    assert result.failures == []


def test_verify_gold_patch_detects_gold_patch_that_breaks_pass_to_pass(tmp_path):
    # The gold patch fixes add but introduces a regression in mul.
    broken_fixed = "def add(a, b):\n    return a + b\n\n\ndef mul(a, b):\n    return a + b\n"
    _write_repo(tmp_path, BUGGY_MODULE, TESTS)
    task = _task(
        tmp_path,
        gold_patch=_make_patch(BUGGY_MODULE, broken_fixed),
    )
    result = verify_gold_patch(task)
    assert result.ok is False
    assert any("pass_to_pass" in f for f in result.failures)


def test_verify_gold_patch_detects_fail_to_pass_not_failing_on_buggy(tmp_path):
    # A "bug" that does not actually break the fail_to_pass test must be caught:
    # fail_to_pass is expected to fail on the buggy baseline.
    _write_repo(tmp_path, GOOD_MODULE, TESTS)
    task = _task(
        tmp_path,
        gold_patch=_make_patch(GOOD_MODULE, GOOD_MODULE + "\n# no-op\n"),
    )
    result = verify_gold_patch(task)
    assert result.ok is False
    assert any("fail_to_pass" in f for f in result.failures)
