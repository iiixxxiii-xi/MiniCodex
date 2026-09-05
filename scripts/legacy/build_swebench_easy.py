"""Build the 48 dependency-light official SWE-bench Lite tasks.

Picks pytest/sphinx/pylint/flask/requests from the official Lite parquet (the
repos that don't need numpy/django-style heavy deps), and builds each via
clone -> checkout base -> apply test_patch -> double-directional verify, using
the swebench-venv (which has the test deps) + PYTHONPATH for imports.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from minicodex.runtime.sandbox.docker import DockerRuntime  # noqa: E402
from build_swebench_tasks import CONFTEST  # noqa: E402

REPOS_DIR = ROOT / "tasks" / "swebench" / "repos"
TASKS_DIR = ROOT / "tasks" / "swebench"
IMAGE = "minicodex-swebench:latest"

EASY_REPOS = {"pytest-dev/pytest", "sphinx-doc/sphinx", "pylint-dev/pylint",
              "pallets/flask", "psf/requests"}


def git(dest, *args, timeout=300):
    return subprocess.run(["git", "-C", str(dest), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=timeout)


def apply_patch(dest, patch):
    p = subprocess.run(["git", "apply", "-"], cwd=str(dest), input=patch,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    return p.returncode == 0


def run_pytest(dest, nodes):
    rt = DockerRuntime(image=IMAGE, mount_path=dest)
    try:
        return rt.run_pytest(nodes, timeout=300)
    finally:
        rt.cleanup()


def checkout(entry):
    dest = REPOS_DIR / entry["instance_id"]
    if not (dest / ".git").exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://github.com/{entry['repo']}.git"
        p = subprocess.run(["git", "clone", "--quiet", url, str(dest)],
                           capture_output=True, text=True, timeout=1800)
        if p.returncode != 0:
            raise RuntimeError(f"clone failed: {p.stderr[:200]}")
    git(dest, "checkout", "--quiet", "--force", entry["base_commit"])
    git(dest, "clean", "-fdq")
    (dest / "conftest.py").write_text(CONFTEST, encoding="utf-8")
    if entry.get("test_patch"):
        if not apply_patch(dest, entry["test_patch"]):
            raise RuntimeError("test_patch apply failed")
    return dest


def validate(entry, dest):
    ftp, ptp = entry["FAIL_TO_PASS"], entry["PASS_TO_PASS"]
    buggy_ftp = run_pytest(dest, ftp)
    buggy_ptp = run_pytest(dest, ptp)
    ftp_buggy_fails = all(not v for v in buggy_ftp.values())
    ptp_buggy_passes = all(buggy_ptp.values())
    if not apply_patch(dest, entry["patch"]):
        return {"ftp_buggy_fails": False, "ptp_buggy_passes": False, "fixed_passes": False}
    fixed = run_pytest(dest, ftp + ptp)
    fixed_passes = all(fixed.values())
    subprocess.run(["git", "apply", "-R", "-"], cwd=str(dest), input=entry["patch"],
                   capture_output=True, text=True, timeout=300)
    return {"ftp_buggy_fails": ftp_buggy_fails, "ptp_buggy_passes": ptp_buggy_passes,
            "fixed_passes": fixed_passes}


def main():
    df = pd.read_parquet(ROOT / "swebench_lite_test.parquet")
    sub = df[df["repo"].isin(EASY_REPOS)]
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    ok = 0
    for _, row in sub.iterrows():
        entry = {
            "instance_id": row["instance_id"], "repo": row["repo"],
            "base_commit": row["base_commit"], "patch": row["patch"],
            "test_patch": row["test_patch"], "problem_statement": row["problem_statement"],
            "FAIL_TO_PASS": json.loads(row["FAIL_TO_PASS"]),
            "PASS_TO_PASS": json.loads(row["PASS_TO_PASS"]),
        }
        try:
            dest = checkout(entry)
            result = validate(entry, dest)
            valid = all(result.values())
            if valid:
                ok += 1
            record = {
                "id": entry["instance_id"], "repo": entry["repo"],
                "instruction": entry["problem_statement"], "gold_patch": entry["patch"],
                "test_command": "pytest -q", "repo_path": str(dest),
                "base_commit": entry["base_commit"],
                "fail_to_pass": entry["FAIL_TO_PASS"],
                "pass_to_pass": entry["PASS_TO_PASS"],
            }
            (TASKS_DIR / f"{entry['instance_id']}.jsonl").write_text(
                json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"[{'OK' if valid else 'INVALID'}] {entry['instance_id']}  {result}", flush=True)
        except Exception as exc:
            print(f"[ERROR] {entry['instance_id']}: {type(exc).__name__}: {exc}", flush=True)
    print(f"\nValid: {ok}/{len(sub)}")


if __name__ == "__main__":
    main()
