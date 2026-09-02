"""SWE-bench style test-matrix verification for tasks.

Two entry points:

* :func:`verify_workspace` — the runner's PASS/FAIL verdict for a patched
  workspace. A task passes only when *every* ``fail_to_pass`` test (tests that
  fail on the buggy baseline) AND *every* ``pass_to_pass`` test (regression
  tests that must stay green) passes.

* :func:`verify_gold_patch` — the build-time double-directional check. On the
  buggy baseline every ``fail_to_pass`` test must FAIL and every ``pass_to_pass``
  test must PASS; after applying ``gold_patch`` every one of them must PASS.

Both operate on a filesystem workspace (a directory laid out like the eval
repos: module + ``conftest.py`` + ``tests/``) and shell out to ``pytest``.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from minicodex.eval.task import Task

# Bytecode is disabled and any cached ``.pyc`` is cleared before each run: a
# stale compiled module (e.g. the buggy one) otherwise survives a patch that
# keeps the source file the same size, making results non-deterministic.
_PYTEST_ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def _clear_pycache(workspace: Path) -> None:
    for pycache in workspace.rglob("__pycache__"):
        if pycache.is_dir():
            shutil.rmtree(pycache, ignore_errors=True)
    for pyc in workspace.rglob("*.pyc"):
        try:
            pyc.unlink()
        except OSError:
            pass


@dataclass
class GoldVerification:
    """The result of double-directional gold-patch verification."""

    task_id: str
    ok: bool = True
    failures: list[str] = field(default_factory=list)


def run_tests(workspace: Path, node_ids: list[str], timeout: float = 120.0) -> dict[str, bool]:
    """Run each pytest node in ``workspace``; return ``{node_id: passed}``.

    Nodes are run individually so a failure can be attributed to the exact test
    that broke (needed to distinguish ``fail_to_pass`` from ``pass_to_pass``
    failures).
    """
    results: dict[str, bool] = {}
    _clear_pycache(workspace)
    for node in node_ids:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", node, "-q", "--no-header", "--tb=no"],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=_PYTEST_ENV,
        )
        results[node] = proc.returncode == 0
    return results


def verify_workspace(task: Task, workspace: Path, timeout: float = 120.0) -> tuple[bool, str, str]:
    """Verdict for a patched workspace against ``task``'s test matrix.

    Returns ``(passed, error, output)``. ``passed`` is True only when every
    ``fail_to_pass`` and every ``pass_to_pass`` test passes. A workspace with no
    matrix at all is a failure (there is nothing to verify).
    """
    ftp = task.fail_to_pass
    ptp = task.pass_to_pass
    if not ftp and not ptp:
        return False, "task has no fail_to_pass/pass_to_pass; cannot determine PASS/FAIL", ""

    results = run_tests(workspace, ftp + ptp, timeout=timeout)
    ftp_failed = [n for n in ftp if not results[n]]
    ptp_failed = [n for n in ptp if not results[n]]

    errors: list[str] = []
    if ftp_failed:
        errors.append(f"fail_to_pass failed: {ftp_failed}")
    if ptp_failed:
        errors.append(f"pass_to_pass failed: {ptp_failed}")
    if errors:
        return False, "; ".join(errors), ""
    return True, "", ""


def _run_grouped(workspace: Path, node_ids: list[str], timeout: float):
    """Run a batch of pytest nodes in a single invocation (for build checks)."""
    return subprocess.run(
        [sys.executable, "-m", "pytest", *node_ids, "-q", "--no-header", "--tb=no"],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=_PYTEST_ENV,
    )


def _summary_counts(proc: subprocess.CompletedProcess) -> tuple[int, int]:
    """Return ``(failed, passed)`` parsed from pytest's summary line."""
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    failed = 0
    passed = 0
    m = re.search(r"(\d+) failed", out)
    if m:
        failed += int(m.group(1))
    m = re.search(r"(\d+) passed", out)
    if m:
        passed += int(m.group(1))
    # pytest reports collection/setup failures as "error(s)".
    for m in re.finditer(r"(\d+) error", out):
        failed += int(m.group(1))
    return failed, passed


def apply_gold_patch(workspace: Path, patch: str, timeout: float = 180.0) -> tuple[bool, str]:
    """Apply a unified diff to ``workspace`` with ``git apply``. Returns ``(ok, err)``."""
    if not patch:
        return False, "empty gold patch"
    proc = subprocess.run(
        ["git", "apply", "-"],
        cwd=str(workspace),
        input=patch.encode("utf-8"),
        capture_output=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        return False, proc.stderr.decode("utf-8", "replace").strip()
    return True, ""


def verify_gold_patch(task: Task, timeout: float = 120.0) -> GoldVerification:
    """Double-directional check of a task's ``gold_patch``.

    * buggy baseline: every ``fail_to_pass`` test fails, every ``pass_to_pass``
      test passes;
    * after applying ``gold_patch``: every ``fail_to_pass`` and ``pass_to_pass``
      test passes.

    Runs against a throwaway copy of ``task.repo_path`` so the real workspace is
    never mutated. Tasks with an empty matrix are trivially OK (legacy
    ``test_command`` tasks are outside this verifier's scope).
    """
    result = GoldVerification(task_id=task.id)
    ftp = task.fail_to_pass
    ptp = task.pass_to_pass
    if not ftp and not ptp:
        return result
    if not task.repo_path:
        result.ok = False
        result.failures.append("task has no repo_path; cannot verify gold patch")
        return result

    repo = Path(task.repo_path)
    with tempfile.TemporaryDirectory(prefix=f"minicodex-verify-{task.id}-") as td:
        ws = Path(td)
        shutil.copytree(repo, ws, dirs_exist_ok=True)
        _clear_pycache(ws)

        all_nodes = ftp + ptp

        # 1. Buggy baseline: every fail_to_pass fails, every pass_to_pass passes.
        proc = _run_grouped(ws, all_nodes, timeout)
        failed, passed = _summary_counts(proc)
        if failed != len(ftp) or passed != len(ptp):
            result.ok = False
            result.failures.append(
                f"buggy baseline mismatch: fail_to_pass should all fail and pass_to_pass "
                f"should all pass (failed={failed}, passed={passed}, "
                f"expected {len(ftp)} failed + {len(ptp)} passed)"
            )

        # 2. Apply the gold patch.
        ok, err = apply_gold_patch(ws, task.gold_patch)
        if not ok:
            result.ok = False
            result.failures.append(f"gold patch failed to apply: {err[:300]}")
            return result
        _clear_pycache(ws)

        # 3. Gold-patched: every fail_to_pass AND pass_to_pass must pass.
        proc = _run_grouped(ws, all_nodes, timeout)
        failed, _ = _summary_counts(proc)
        if failed > 0:
            result.ok = False
            result.failures.append(
                f"fail_to_pass/pass_to_pass failing after gold patch (failed={failed})"
            )

    return result


__all__ = ["GoldVerification", "apply_gold_patch", "run_tests", "verify_gold_patch", "verify_workspace"]
