"""Build + validate real repo-level SWE-bench tasks from upstream git history.

Unlike ``build_swebench_subset.py`` (which hand-pins two tasks), this builder
*auto-discovers* candidate bug-fix commits across a set of small, actively
maintained repositories and turns each into a validated SWE-bench record.

For each repository the script:

1. clones the upstream repo (full history, so ``base_commit`` = parent of the
   fix commit is reachable);
2. scans ``git log`` for bug-fix commits (subject matches "fix"/"bug"/... ) and
   filters out non-functional churn (typo/lint/format/docs/CI commits and
   commits that touch too many files to be a focused fix);
3. for every surviving commit that touches BOTH source and test files it
   derives ``gold_patch`` (source diff) and ``test_patch`` (test diff);
4. checks out ``base_commit``, drops in a root ``conftest.py`` that makes the
   ``src``- or flat-layout package importable, and applies ``test_patch``;
5. derives the FAIL_TO_PASS / PASS_TO_PASS matrix by running every test in the
   touched test files on the buggy baseline and again after ``gold_patch``
   (FAIL_TO_PASS = fails-buggy & passes-fixed, PASS_TO_PASS = passes both);
6. performs the SWE-bench double-directional check (buggy: FTP fails + PTP
   passes; fixed: everything passes) and only keeps commits that hold;
7. reverts the gold fix, leaving ``buggy source + test_patch`` for the agent,
   and writes one ``tasks/swebench/*.jsonl`` record per valid task.

Run with::

    uv run python scripts/build_swebench_tasks.py [--max-per-repo 4]

Validation runs inside a dedicated venv (``--venv``) so the project environment
is never polluted with per-repo test dependencies.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows: the default GBK codec cannot encode
# non-ASCII commit subjects (e.g. emoji U+1F527), which crashes the [skip]
# progress print mid-build.
for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
REPOS_DIR = ROOT / "tasks" / "swebench" / "repos"
TASKS_DIR = ROOT / "tasks" / "swebench"

# Insert both the repo root and its ``src/`` directory so both flat-layout
# (``rich``, ``tqdm``) and src-layout (``click``, ``jinja2``, ``werkzeug``,
# ``urllib3``) packages are importable without an editable install.
CONFTEST = (
    "import os, sys\n"
    'root = os.path.dirname(os.path.abspath(__file__))\n'
    'for p in (root, os.path.join(root, "src")):\n'
    '    if os.path.isdir(p) and p not in sys.path:\n'
    "        sys.path.insert(0, p)\n"
)

# repo key -> (upstream slug, python package name, clone URL)
REPOS: dict[str, tuple[str, str, str]] = {
    "click": ("pallets/click", "click", "https://github.com/pallets/click.git"),
    "jinja2": ("pallets/jinja", "jinja2", "https://github.com/pallets/jinja.git"),
    "werkzeug": ("pallets/werkzeug", "werkzeug", "https://github.com/pallets/werkzeug.git"),
    "rich": ("Textualize/rich", "rich", "https://github.com/Textualize/rich.git"),
    "tqdm": ("tqdm/tqdm", "tqdm", "https://github.com/tqdm/tqdm.git"),
    "urllib3": ("urllib3/urllib3", "urllib3", "https://github.com/urllib3/urllib3.git"),
    "flask": ("pallets/flask", "flask", "https://github.com/pallets/flask.git"),
    "requests": ("psf/requests", "requests", "https://github.com/psf/requests.git"),
    "httpx": ("encode/httpx", "httpx", "https://github.com/encode/httpx.git"),
    "pydantic": ("pydantic/pydantic", "pydantic", "https://github.com/pydantic/pydantic.git"),
    "sqlalchemy": ("sqlalchemy/sqlalchemy", "sqlalchemy", "https://github.com/sqlalchemy/sqlalchemy.git"),
    "itsdangerous": ("pallets/itsdangerous", "itsdangerous", "https://github.com/pallets/itsdangerous.git"),
    "markupsafe": ("pallets/markupsafe", "markupsafe", "https://github.com/pallets/markupsafe.git"),
    "blinker": ("pallets-eco/blinker", "blinker", "https://github.com/pallets-eco/blinker.git"),
    "h11": ("python-hyper/h11", "h11", "https://github.com/python-hyper/h11.git"),
    "httpcore": ("encode/httpcore", "httpcore", "https://github.com/encode/httpcore.git"),
    "anyio": ("agronholm/anyio", "anyio", "https://github.com/agronholm/anyio.git"),
    "sniffio": ("python-trio/sniffio", "sniffio", "https://github.com/python-trio/sniffio.git"),
    "idna": ("kjd/idna", "idna", "https://github.com/kjd/idna.git"),
    "wcwidth": ("jquast/wcwidth", "wcwidth", "https://github.com/jquast/wcwidth.git"),
    "humanize": ("python-humanize/humanize", "humanize", "https://github.com/python-humanize/humanize.git"),
    "packaging": ("pypa/packaging", "packaging", "https://github.com/pypa/packaging.git"),
    "platformdirs": ("platformdirs/platformdirs", "platformdirs", "https://github.com/platformdirs/platformdirs.git"),
    "colorama": ("tartley/colorama", "colorama", "https://github.com/tartley/colorama.git"),
    "more-itertools": ("more-itertools/more-itertools", "more_itertools", "https://github.com/more-itertools/more-itertools.git"),
}

# Commit subjects that indicate non-functional churn; skipped during discovery.
_JUNK_SUBJECT = re.compile(
    r"lint|typo|codespell|pyright|mypy|flake8|ruff|format|readme|changelog|"
    r"docs|documentation|ci\b|bump|dependabot|version|release|style|merge|"
    r"refactor|pre-commit|github actions|workflow|coverage|nit\b|cleanup|"
    r"deprecat",
    re.IGNORECASE,
)
_GREP = ["fix", "bug", "wrong", "incorrect", "crash", "overflow", "handle", "should"]
_MAX_SOURCE_FILES = 3
_MAX_TEST_FILES = 3
_MAX_NODES_PER_PHASE = 400  # safety cap on per-file test collection


def run(argv: list[str], *, cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )


def git(repo_dir: Path, *args: str, timeout: int = 300) -> subprocess.CompletedProcess:
    return run(["git", *args], cwd=repo_dir, timeout=timeout)


def is_test_file(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    base = parts[-1]
    return (
        any(x in ("tests", "test") for x in parts[:-1])
        or base.startswith("test_")
        or base.endswith("_test.py")
        or base == "tests.py"
    )


def is_source_file(path: str, package: str) -> bool:
    if not path.endswith(".py"):
        return False
    if is_test_file(path):
        return False
    p = path.replace("\\", "/")
    return package in p or "/src/" in p


def collect_nodes(repo_dir: Path, test_files: list[str], python: str) -> list[str]:
    """Return the pytest node ids collected from ``test_files`` (empty on error)."""
    proc = run(
        [python, "-m", "pytest", "--collect-only", "-q", *test_files],
        cwd=repo_dir, timeout=300,
    )
    nodes: list[str] = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        # Node ids look like ``<path>.py::<node>`` (possibly with ``[...]`` params);
        # summary/warning/error lines never start with a ``.py::`` path.
        if re.match(r"^[\w./\\-]+\.py::", line):
            nodes.append(line)
    return nodes


def run_nodes(repo_dir: Path, nodes: list[str], python: str) -> dict[str, bool]:
    """Run each node individually; return ``{node: passed}`` (parallelised)."""
    def _one(node: str) -> tuple[str, bool]:
        proc = run(
            [python, "-m", "pytest", node, "-q", "--no-header", "--tb=no"],
            cwd=repo_dir, timeout=300,
        )
        return node, proc.returncode == 0

    results: dict[str, bool] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for node, passed in pool.map(_one, nodes):
            results[node] = passed
    return results


def apply_patch(repo_dir: Path, patch: str) -> bool:
    if not patch.strip():
        return False
    proc = subprocess.run(
        ["git", "apply", "-"], cwd=str(repo_dir), input=patch.encode("utf-8"),
        capture_output=True, timeout=300,
    )
    return proc.returncode == 0


def revert_files(repo_dir: Path, files: list[str]) -> None:
    git(repo_dir, "checkout", "--quiet", "--", *files)


def clone(repo_key: str, url: str) -> Path:
    """Clone (once) into ``tasks/swebench/repos/_clone_<key>`` as the source of
    history; task workspaces are separate checkouts."""
    dest = REPOS_DIR / f"_clone_{repo_key}"
    if not (dest / ".git").exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        proc = run(["git", "clone", "--quiet", url, str(dest)], cwd=ROOT, timeout=900)
        if proc.returncode != 0:
            raise RuntimeError(f"clone failed for {url}: {proc.stderr.strip()[:300]}")
    git(dest, "fetch", "--quiet", "origin")
    return dest


def discover_fix_commits(clone_dir: Path, package: str) -> list[tuple[str, str]]:
    """Return ``(sha, subject)`` for fix commits touching both source and tests."""
    grep_args: list[str] = []
    for g in _GREP:
        grep_args += ["--grep", g]
    proc = git(clone_dir, "log", "--no-merges", "-i", "--format=%H%x1f%s", *grep_args)
    out: list[tuple[str, str]] = []
    for line in (proc.stdout or "").splitlines():
        if "\x1f" not in line:
            continue
        sha, subject = line.split("\x1f", 1)
        if _JUNK_SUBJECT.search(subject):
            continue
        names = git(clone_dir, "show", "--name-only", "--format=", sha).stdout.split()
        src = [f for f in names if is_source_file(f, package)]
        tst = [f for f in names if is_test_file(f)]
        if not src or not tst:
            continue
        if len(src) > _MAX_SOURCE_FILES or len(tst) > _MAX_TEST_FILES:
            continue
        out.append((sha, subject.strip()))
    return out


def make_problem_statement(clone_dir: Path, sha: str) -> str:
    """Synthesise a SWE-bench-style problem statement from the commit message."""
    body = git(clone_dir, "show", "-s", "--format=%B", sha).stdout.strip()
    # Drop trailing git trailers (Fixes:, Closes:, Co-authored-by:, ...).
    lines = [ln for ln in body.splitlines() if not re.match(r"^(fixes|closes|see|"
             r"co-authored-by|signed-off-by|reviewed-by|reported-by):", ln, re.IGNORECASE)]
    text = "\n".join(lines).strip()
    return text


def build_task(
    clone_dir: Path,
    repo_key: str,
    package: str,
    sha: str,
    subject: str,
    python: str,
) -> dict | None:
    """Build + validate one task; return the record dict, or None if invalid."""
    base_commit = git(clone_dir, "rev-parse", f"{sha}^").stdout.strip()
    if not base_commit or base_commit == sha:
        return None

    names = git(clone_dir, "show", "--name-only", "--format=", sha).stdout.split()
    src_files = [f for f in names if is_source_file(f, package)]
    tst_files = [f for f in names if is_test_file(f)]
    if not src_files or not tst_files:
        return None

    gold_patch = git(clone_dir, "diff", base_commit, sha, "--", *src_files).stdout
    test_patch = git(clone_dir, "diff", base_commit, sha, "--", *tst_files).stdout
    if not gold_patch.strip() or not test_patch.strip():
        return None

    instance_id = f"{package}__{package}-{sha[:8]}"
    workspace = REPOS_DIR / instance_id

    # Fresh workspace at the buggy revision.
    if workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)
    proc = run(["git", "clone", "--quiet", str(clone_dir), str(workspace)], cwd=ROOT, timeout=900)
    if proc.returncode != 0:
        return None
    git(workspace, "checkout", "--quiet", "--force", base_commit)
    git(workspace, "clean", "-fdq")
    (workspace / "conftest.py").write_text(CONFTEST, encoding="utf-8")

    # The test files in the fix commit may not exist at base_commit (new files),
    # so apply test_patch via ``git apply`` (which can create them).
    if not apply_patch(workspace, test_patch):
        shutil.rmtree(workspace, ignore_errors=True)
        return None

    # Collect the tests the fix touches (files must exist post test_patch).
    present_tests = [t for t in tst_files if (workspace / t).exists()]
    if not present_tests:
        shutil.rmtree(workspace, ignore_errors=True)
        return None
    nodes = collect_nodes(workspace, present_tests, python)
    if not nodes:
        shutil.rmtree(workspace, ignore_errors=True)
        return None
    nodes = nodes[:_MAX_NODES_PER_PHASE]

    buggy = run_nodes(workspace, nodes, python)

    # Copy, apply gold, and re-run to find the fixed status.
    fixed_ws = workspace.parent / f"{instance_id}.fixed"
    shutil.rmtree(fixed_ws, ignore_errors=True)
    shutil.copytree(workspace, fixed_ws)
    if not apply_patch(fixed_ws, gold_patch):
        shutil.rmtree(fixed_ws, ignore_errors=True)
        shutil.rmtree(workspace, ignore_errors=True)
        return None
    fixed = run_nodes(fixed_ws, nodes, python)

    ftp = [n for n in nodes if not buggy.get(n, False) and fixed.get(n, True)]
    ptp = [n for n in nodes if buggy.get(n, False) and fixed.get(n, True)]
    # Only FAIL_TO_PASS is required: many candidate commits have their
    # PASS_TO_PASS regressions fail on the buggy baseline for environment
    # reasons (deps), not because the fix is wrong. Accept ftp-only tasks.
    if not ftp:
        shutil.rmtree(fixed_ws, ignore_errors=True)
        shutil.rmtree(workspace, ignore_errors=True)
        return None

    # Cap PASS_TO_PASS to a small sample for fast hidden-test verification.
    ptp = ptp[:3]

    # Final check: fail_to_pass fails on buggy, everything passes on fixed.
    buggy_ftp = run_nodes(workspace, ftp, python)
    fixed_all = run_nodes(fixed_ws, ftp + ptp, python)
    ok = (
        all(not passed for passed in buggy_ftp.values())
        and all(fixed_all.values())
    )

    shutil.rmtree(fixed_ws, ignore_errors=True)
    if not ok:
        shutil.rmtree(workspace, ignore_errors=True)
        return None

    record = {
        "instance_id": instance_id,
        "repo": repo_key,
        "base_commit": base_commit,
        "problem_statement": make_problem_statement(clone_dir, sha),
        "patch": gold_patch,
        "test_patch": test_patch,
        "FAIL_TO_PASS": ftp,
        "PASS_TO_PASS": ptp,
        "test_command": "pytest -q",
        "difficulty": "hard",
        "install_command": "",
    }
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-per-repo", type=int, default=4)
    parser.add_argument("--venv", default=None,
                        help="Dedicated venv used for test validation "
                             "(default: <tmp>/swebench-venv).")
    parser.add_argument("--repos", default=None,
                        help="Comma-separated repo keys to build (default: all).")
    args = parser.parse_args()

    import tempfile

    venv_dir = Path(args.venv) if args.venv else Path(tempfile.gettempdir()) / "swebench-venv"
    python = venv_dir / "Scripts" / "python.exe"
    if not python.exists():
        python = venv_dir / "bin" / "python"
    if not python.exists():
        raise SystemExit(f"validation venv python not found: {python}")

    keys = [k.strip() for k in (args.repos or "").split(",") if k.strip()] or list(REPOS)
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    TASKS_DIR.mkdir(parents=True, exist_ok=True)

    total = 0
    report: dict[str, list[str]] = {}
    for key in keys:
        slug, package, url = REPOS[key]
        print(f"\n=== {key} ({slug}) ===")
        try:
            clone_dir = clone(key, url)
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"  [clone-error] {exc}")
            continue
        commits = discover_fix_commits(clone_dir, package)
        print(f"  {len(commits)} candidate fix commits")
        made = 0
        for sha, subject in commits:
            if made >= args.max_per_repo:
                break
            try:
                record = build_task(clone_dir, key, package, sha, subject, python)
            except Exception as exc:  # noqa: BLE001 - never abort the batch
                print(f"  [error] {sha[:8]} {subject[:60]}: {exc}")
                continue
            if record is None:
                print(f"  [skip] {sha[:8]} {subject[:60]}")
                continue
            out_path = TASKS_DIR / f"{record['instance_id']}.jsonl"
            out_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"  [ok] {record['instance_id']}  FTP={len(record['FAIL_TO_PASS'])} "
                  f"PTP={len(record['PASS_TO_PASS'])}  {subject[:55]}")
            report.setdefault(key, []).append(record["instance_id"])
            made += 1
            total += 1

    print(f"\nBuilt {total} valid tasks across {len(report)} repos -> {TASKS_DIR}")
    for key, ids in report.items():
        print(f"  {key}: {len(ids)}")
    return 0 if total > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
