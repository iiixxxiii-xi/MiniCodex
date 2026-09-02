"""Build + validate the SWE-bench subset into ``tasks/swebench/``.

For each task this script:

1. clones the real upstream repo (with a timeout) and checks out ``base_commit``
   (the buggy revision);
2. adds a root ``conftest.py`` so a ``src/``-layout package is importable inside
   the sandbox without an editable install;
3. applies ``test_patch`` (the tests that demonstrate the bug);
4. validates the double-directional property: on the buggy baseline every
   ``FAIL_TO_PASS`` test fails and every ``PASS_TO_PASS`` test passes; after
   applying ``patch`` (the gold fix) everything passes;
5. reverts the gold fix, leaving ``buggy source + test_patch`` for the agent,
   and writes the SWE-bench-format JSONL record.

Run with: ``uv run python scripts/build_swebench_subset.py``
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPOS_DIR = ROOT / "tasks" / "swebench" / "repos"
TASKS_DIR = ROOT / "tasks" / "swebench"

CONFTEST = (
    'import os\nimport sys\n\n'
    'sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))\n'
)

# Extra test_patch for markupsafe: the fix commit only touched source, so the
# regression test (from the same PR, added later) is supplied explicitly.
MARKUPSAFE_TEST_PATCH = """\
diff --git a/tests/test_escape.py b/tests/test_escape.py
index 03e0b64..1b233aa 100644
--- a/tests/test_escape.py
+++ b/tests/test_escape.py
@@ -30,3 +30,24 @@ from markupsafe import Markup
 )
 def test_escape(value: str, expect: str) -> None:
     assert escape(value) == Markup(expect)
+
+
+class Proxy:
+    def __init__(self, value):
+        self.__value = value
+
+    @property
+    def __class__(self):
+        # Make o.__class__ and isinstance(o, str) see the proxied object.
+        return self.__value.__class__
+
+    def __str__(self):
+        return str(self.__value)
+
+
+def test_proxy() -> None:
+    \"\"\"Handle a proxy object that pretends its __class__ is str.\"\"\"
+    p = Proxy("test")
+    assert p.__class__ is str
+    assert isinstance(p, str)
+    assert escape(p) == Markup("test")
+"""


TASKS: list[dict] = [
    {
        "instance_id": "markupsafe__markupsafe-467",
        "repo": "pallets/markupsafe",
        "url": "https://github.com/pallets/markupsafe.git",
        "base_commit": "b5291646cbabf945069db07c34b08fb1f623134d",
        "fix_commit": "7add29c77b088299841e1017a7cd2f96133a6659",
        "source_paths": ["src/markupsafe/__init__.py"],
        "test_paths": [],
        "test_patch": MARKUPSAFE_TEST_PATCH,
        "problem_statement": (
            "``escape`` detects a plain string with ``s.__class__ is str``. A proxy "
            "object that reports the proxied value's ``__class__`` (so "
            "``p.__class__ is str`` is True) is then sent down the fast path and "
            "escaped as if it were a real str, which raises ``AttributeError``. "
            "Change the check to ``type(s) is str`` so proxies are escaped via "
            "``str(s)`` instead."
        ),
        "fail_to_pass": ["tests/test_escape.py::test_proxy[markupsafe._native]"],
        "pass_to_pass": [
            "tests/test_markupsafe.py::test_adding[markupsafe._native]",
            "tests/test_markupsafe.py::test_type_behavior[markupsafe._native]",
        ],
    },
    {
        "instance_id": "click__click-3677",
        "repo": "pallets/click",
        "url": "https://github.com/pallets/click.git",
        "base_commit": "7925a3410d7098c28cfca3b2baa6c852666bbd14",
        "fix_commit": "07c909f23f0f83b5ca137c167b9a134d66201f67",
        "source_paths": ["src/click/termui.py"],
        "test_paths": ["tests/test_utils/test_style.py"],
        "test_patch": None,
        "problem_statement": (
            "``style()`` and ``secho()`` silently drop the 256-color index 0 "
            "(black) passed as ``fg``/``bg`` because the code checks truthiness of "
            "the color, and invalid colors are not validated. Rewrite "
            "``_interpret_color`` so index 0 is honoured and invalid color values "
            "raise ``ValueError``."
        ),
        "fail_to_pass": ["tests/test_utils/test_style.py::test_styling_invalid_color"],
        "pass_to_pass": ["tests/test_utils/test_style.py::test_unstyle_other_ansi"],
    },
]


def run(argv: list[str], *, cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout,
    )


def git(repo_dir: Path, *args: str, timeout: int = 300) -> subprocess.CompletedProcess:
    return run(["git", *args], cwd=repo_dir, timeout=timeout)


def apply_patch(repo_dir: Path, patch: str) -> None:
    proc = subprocess.run(
        ["git", "apply", "-"],
        cwd=str(repo_dir),
        input=patch,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git apply failed: {proc.stderr.strip()}")


def run_pytest(repo_dir: Path, nodes: list[str]) -> bool:
    proc = run(
        [sys.executable, "-m", "pytest", *nodes, "-q", "--no-header", "--tb=no"],
        cwd=repo_dir, timeout=600,
    )
    return proc.returncode == 0


def checkout(entry: dict) -> Path:
    """Clone (once) and check out ``base_commit``, then add conftest + test_patch."""
    dest = REPOS_DIR / entry["instance_id"]
    if not (dest / ".git").exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        proc = run(["git", "clone", "--quiet", entry["url"], str(dest)], cwd=ROOT, timeout=600)
        if proc.returncode != 0:
            raise RuntimeError(f"clone failed: {proc.stderr.strip()}")

    git(dest, "checkout", "--quiet", "--force", entry["base_commit"])
    git(dest, "clean", "-fdq")

    # Make the src-layout package importable inside the sandbox.
    (dest / "conftest.py").write_text(CONFTEST, encoding="utf-8")

    # Derive the gold patch from base..fix restricted to source.
    gold = git(dest, "diff", entry["base_commit"], entry["fix_commit"], "--", *entry["source_paths"])
    if gold.returncode != 0:
        raise RuntimeError(f"gold diff failed: {gold.stderr.strip()}")

    # Test patch is either explicit (markupsafe) or derived from base..fix tests.
    test_patch = entry["test_patch"]
    if test_patch is None:
        tp = git(dest, "diff", entry["base_commit"], entry["fix_commit"], "--", *entry["test_paths"])
        if tp.returncode != 0:
            raise RuntimeError(f"test diff failed: {tp.stderr.strip()}")
        test_patch = tp.stdout

    apply_patch(dest, test_patch)
    entry["_gold_patch"] = gold.stdout
    entry["_test_patch"] = test_patch
    return dest


def validate(entry: dict, dest: Path) -> dict:
    ftp = entry["fail_to_pass"]
    ptp = entry["pass_to_pass"]

    # Buggy baseline: FTP must fail, PTP must pass.
    ftp_buggy = run_pytest(dest, ftp)
    ptp_buggy = run_pytest(dest, ptp)

    # Apply the gold fix, re-check, then revert it.
    apply_patch(dest, entry["_gold_patch"])
    ftp_fixed = run_pytest(dest, ftp + ptp)
    git(dest, "checkout", "--quiet", "--", *entry["source_paths"])

    return {
        "ftp_buggy_fails": not ftp_buggy,
        "ptp_buggy_passes": ptp_buggy,
        "ftp_ptp_fixed_passes": ftp_fixed,
    }


def main() -> int:
    shutil.rmtree(REPOS_DIR, ignore_errors=True)
    TASKS_DIR.mkdir(parents=True, exist_ok=True)

    all_ok = True
    records: list[dict] = []
    for entry in TASKS:
        try:
            dest = checkout(entry)
            result = validate(entry, dest)
            ok = all(result.values())
            all_ok &= ok
            record = {
                "instance_id": entry["instance_id"],
                "repo": entry["repo"],
                "base_commit": entry["base_commit"],
                "problem_statement": entry["problem_statement"],
                "patch": entry["_gold_patch"],
                "test_patch": entry["_test_patch"],
                "FAIL_TO_PASS": entry["fail_to_pass"],
                "PASS_TO_PASS": entry["pass_to_pass"],
                "test_command": "pytest -q",
            }
            records.append(record)
            status = "OK" if ok else "INVALID"
            print(f"[{status}] {entry['instance_id']}  {result}")
            (TASKS_DIR / f"{entry['instance_id']}.jsonl").write_text(
                json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        except Exception as exc:  # noqa: BLE001 - report and continue
            all_ok = False
            print(f"[ERROR] {entry['instance_id']}: {exc}")

    print(f"\nValid: {sum(1 for r in records)}  tasks written to {TASKS_DIR}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
