"""Build 50 official SWE-bench Lite tasks into ``tasks/swebench50/``.

Unlike ``build_swebench_subset.py`` (2 hand-pinned) and ``build_swebench_tasks.py``
(auto-discover bug-fix commits), this reads the official SWE-bench Lite records
(``swebench_50.json``, a stratified 50-task sample) whose ``patch``/``test_patch``
are already given. For each task it: clones the upstream repo, checks out
``base_commit``, applies ``test_patch``, installs the package (``pip install -e .``),
then double-directionally verifies (buggy: FAIL_TO_PASS fails + PASS_TO_PASS
passes; gold: everything passes) and writes the SWE-bench JSONL record.

Run: ``uv run python scripts/build_swebench_50.py``
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPOS_DIR = ROOT / "tasks" / "swebench50" / "repos"
TASKS_DIR = ROOT / "tasks" / "swebench50"
PY = ROOT / ".venv" / "Scripts" / "python.exe"
PIP = ROOT / ".venv" / "Scripts" / "pip.exe"


def repo_url(repo: str) -> str:
    return f"https://github.com/{repo}.git"


def _as_list(x):
    """The parquet stores FAIL_TO_PASS/PASS_TO_PASS as JSON strings; normalize."""
    if isinstance(x, str):
        return json.loads(x)
    return x


def git(dest: Path, *args: str, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(dest), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=timeout)


def apply_patch(dest: Path, patch: str) -> None:
    proc = subprocess.run(["git", "apply", "-"], cwd=str(dest), input=patch,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(f"git apply failed: {proc.stderr.strip()[:300]}")


def checkout(entry: dict) -> Path:
    dest = REPOS_DIR / entry["instance_id"]
    if not (dest / ".git").exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(["git", "clone", "--quiet", repo_url(entry["repo"]), str(dest)],
                              capture_output=True, text=True, timeout=1800)
        if proc.returncode != 0:
            raise RuntimeError(f"clone failed: {proc.stderr.strip()[:300]}")
    git(dest, "checkout", "--quiet", "--force", entry["base_commit"])
    git(dest, "clean", "-fdq")
    if entry.get("test_patch"):
        apply_patch(dest, entry["test_patch"])
    return dest


def install(dest: Path) -> None:
    """Install the package into the shared venv (best-effort, not fatal)."""
    proc = subprocess.run(["uv", "pip", "install", "-e", ".", "--python", str(PY), "--quiet"],
                          cwd=str(dest), capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        print(f"    [install-warn] {proc.stderr.strip()[:200]}")


def run_pytest(dest: Path, nodes: list[str]) -> bool:
    env = {**os.environ, "PYTHONPATH": str(dest)}
    proc = subprocess.run([str(PY), "-m", "pytest", *nodes, "-q", "--no-header", "--tb=no"],
                          cwd=str(dest), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=900, env=env)
    return proc.returncode == 0


def validate(entry: dict, dest: Path) -> dict:
    ftp, ptp = entry["FAIL_TO_PASS"], entry["PASS_TO_PASS"]
    ftp_buggy = run_pytest(dest, ftp)
    ptp_buggy = run_pytest(dest, ptp)
    apply_patch(dest, entry["patch"])
    ftp_fixed = run_pytest(dest, ftp + ptp)
    # revert the gold patch, keep test_patch for the agent.
    subprocess.run(["git", "apply", "-R", "-"], cwd=str(dest), input=entry["patch"],
                   capture_output=True, text=True, timeout=300)
    return {"ftp_buggy_fails": not ftp_buggy, "ptp_buggy_passes": ptp_buggy,
            "ftp_ptp_fixed_passes": ftp_fixed}


def main() -> int:
    records = json.loads((ROOT / "swebench_50.json").read_text(encoding="utf-8"))
    for entry in records:
        entry["FAIL_TO_PASS"] = _as_list(entry["FAIL_TO_PASS"])
        entry["PASS_TO_PASS"] = _as_list(entry["PASS_TO_PASS"])
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    ok = 0
    for entry in records:
        try:
            dest = checkout(entry)
            install(dest)
            result = validate(entry, dest)
            valid = all(result.values())
            if valid:
                ok += 1
            record = {
                "id": entry["instance_id"],
                "repo": entry["repo"],
                "instruction": entry["problem_statement"],
                "gold_patch": entry["patch"],
                "test_command": "pytest -q",
                "repo_path": str(dest),
                "base_commit": entry["base_commit"],
                "fail_to_pass": entry["FAIL_TO_PASS"],
                "pass_to_pass": entry["PASS_TO_PASS"],
            }
            (TASKS_DIR / f"{entry['instance_id']}.jsonl").write_text(
                json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            print(f"[{'OK' if valid else 'INVALID'}] {entry['instance_id']}  {result}")
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"[ERROR] {entry['instance_id']}: {type(exc).__name__}: {exc}")
    print(f"\nValid: {ok}/{len(records)}  written to {TASKS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
