"""Build the minicodex repo-level task set (SWE-bench style) and verify it.

This script is the single source of truth for the hand-crafted repo-level tasks.
Each repo is now a *multi-module package* (not a single toy module): a small,
realistic library laid out across several source files with cross-module
imports. For each repo, ``scripts/task_specs/<repo>.py`` defines:

  * ``REPO``  — the repo/package name.
  * ``FILES`` — ``{relative_path: correct_source}`` for every source file.
  * ``TESTS`` — ``{relative_path: test_source}`` for every test file.
  * ``TASKS`` — one dict per task, each injecting ONE realistic bug (a list of
    ``(path, correct_snippet, buggy_snippet)`` edits — a bug may span modules).

Building materialises, per task, the buggy package plus its tests under
``tasks/repos/<repo>/<task-id>/`` and a flat ``tasks/<id>.json`` carrying a
``fail_to_pass`` / ``pass_to_pass`` test matrix (full pytest node ids) plus the
real ``gold_patch`` (a multi-file diff from the buggy package back to correct).

After building, every task is verified double-directionally with the shared
verifier (``minicodex.eval.verification.verify_gold_patch``):

  1. buggy baseline  -> every fail_to_pass test FAILS, every pass_to_pass PASSES
  2. apply gold_patch -> every fail_to_pass AND pass_to_pass test PASSES

Run::

    uv run python scripts/build_tasks.py                 # full clean rebuild
    uv run python scripts/build_tasks.py --check-repo codec   # verify one repo in a temp dir
"""

from __future__ import annotations

import argparse
import difflib
import importlib
import json
import pkgutil
import shutil
import sys
import tempfile
from pathlib import Path

from minicodex.eval.task import Task
from minicodex.eval.verification import verify_gold_patch

# Ensure ``task_specs`` (a sibling package) is importable however this script is
# invoked (``python scripts/build_tasks.py`` puts ``scripts/`` on sys.path[0]).
sys.path.insert(0, str(Path(__file__).resolve().parent))

import task_specs  # noqa: E402

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


def apply_edits(files: dict[str, str], edits: list[tuple[str, str, str]]) -> dict[str, str]:
    """Return a copy of ``files`` with each ``(path, correct, buggy)`` edit applied.

    Edits are applied in order; an edit targeting an unknown path, or an anchor
    that is not unique within its file, raises ``ValueError``.
    """
    out = dict(files)
    for path, old, new in edits:
        if path not in out:
            raise ValueError(f"edit references unknown file: {path}")
        out[path] = apply_fix(out[path], old, new)
    return out


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


def make_multi_patch(buggy_files: dict[str, str], fixed_files: dict[str, str]) -> str:
    """Return a git apply-able multi-file diff turning ``buggy_files`` into ``fixed_files``."""
    chunks = []
    for path in sorted(set(buggy_files) | set(fixed_files)):
        buggy = buggy_files.get(path, "")
        fixed = fixed_files.get(path, "")
        if buggy == fixed:
            continue
        chunks.append(make_patch(buggy, fixed, path))
    return "".join(chunks)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def discover_specs() -> list:
    """Return every repo spec module found in ``task_specs`` (sorted by name)."""
    specs = []
    for mod in sorted(pkgutil.iter_modules(task_specs.__path__), key=lambda m: m.name):
        if mod.name.startswith("_"):
            continue
        module = importlib.import_module(f"task_specs.{mod.name}")
        if all(hasattr(module, attr) for attr in ("REPO", "FILES", "TESTS", "TASKS")):
            specs.append(module)
    return specs


def find_spec(name: str):
    for spec in discover_specs():
        if spec.REPO == name:
            return spec
    raise SystemExit(f"unknown repo: {name}")


def build_repo(spec, repos_dir: Path, tasks_dir: Path, repo_path_prefix: str) -> list[Task]:
    """Materialise one repo's tasks. Returns the list of ``Task`` objects.

    ``repo_path_prefix`` becomes the leading component of each task's
    ``repo_path`` (``"tasks/repos"`` for the real build, an absolute temp path
    for an isolated ``--check-repo`` run).
    """
    tasks: list[Task] = []
    for t in spec.TASKS:
        buggy_files = apply_edits(spec.FILES, t["bug"])
        patch = make_multi_patch(buggy_files, spec.FILES)
        if not patch:
            raise ValueError(f"empty gold_patch for {t['id']}")

        task_dir = repos_dir / spec.REPO / t["id"]
        for rel, content in buggy_files.items():
            write_text(task_dir / rel, content)
        write_text(task_dir / "conftest.py", CONFTEST)
        for rel, content in spec.TESTS.items():
            write_text(task_dir / rel, content)

        task = Task(
            id=t["id"],
            repo=spec.REPO,
            instruction=t["instruction"],
            gold_patch=patch,
            repo_path=f"{repo_path_prefix}/{spec.REPO}/{t['id']}",
            fail_to_pass=list(t["fail_to_pass"]),
            pass_to_pass=list(t["pass_to_pass"]),
            metadata={
                "difficulty": t["difficulty"],
                "category": t["category"],
                "estimated_lines": t["lines"],
            },
        )
        write_text(tasks_dir / f"{t['id']}.json", json.dumps(task.model_dump(), indent=2, ensure_ascii=False) + "\n")
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-repo",
        help="build + verify a single repo into a throwaway temp dir (touches nothing in tasks/).",
    )
    parser.add_argument(
        "--repo",
        help="full build of only this repo (cleans that repo's existing tasks).",
    )
    args = parser.parse_args(argv)

    if args.check_repo:
        spec = find_spec(args.check_repo)
        with tempfile.TemporaryDirectory(prefix=f"minicodex-check-{args.check_repo}-") as td:
            td = Path(td)
            tasks = build_repo(spec, td / "repos", td / "tasks", str((td / "repos").resolve()))
            print(f"checking {len(tasks)} task(s) for repo '{spec.REPO}'")
            return verify(tasks)

    if args.repo:
        spec = find_spec(args.repo)
        specs = [spec]
        for f in TASKS_DIR.glob(f"{args.repo}-*.json"):
            f.unlink()
        shutil.rmtree(REPOS_DIR / args.repo, ignore_errors=True)
    else:
        specs = discover_specs()
        for f in TASKS_DIR.glob("*.json"):
            f.unlink()
        for child in REPOS_DIR.iterdir():
            if child.is_dir():
                shutil.rmtree(child)

    if not specs:
        raise SystemExit("no repo specs found in scripts/task_specs/")

    tasks: list[Task] = []
    for spec in specs:
        tasks.extend(build_repo(spec, REPOS_DIR, TASKS_DIR, "tasks/repos"))
    print(f"built {len(tasks)} tasks across {len(specs)} repos")
    return verify(tasks)


if __name__ == "__main__":
    raise SystemExit(main())
