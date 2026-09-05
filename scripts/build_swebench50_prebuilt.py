"""Build the 50-instance SWE-bench Lite subset from official pre-built images.

The official SWE-bench harness publishes a prebuilt Docker image per instance
(``swebench/sweb.eval.x86_64.<owner>_1776_<repo>-<issue>``) with the repo checked
out at ``base_commit`` in ``/testbed`` and a conda env ``testbed`` holding the
era-correct dependencies. This builder, for each instance:

1. computes the image name from ``instance_id`` and pulls the image (skips if
   already local — the pull goes through the configured Docker proxy);
2. extracts ``/testbed`` (the repo at ``base_commit``) to
   ``tasks/swebench50/repos/<instance_id>``;
3. applies ``test_patch`` (the tests that demonstrate the bug);
4. validates the SWE-bench double-directional property inside the image's conda
   env (F2P fails on the buggy baseline, P2P passes, everything passes after the
   gold patch) and only keeps instances that hold;
5. writes one ``tasks/swebench50/<instance_id>.jsonl`` task record with
   ``repo_path`` pointing at the extracted checkout.

Run::

    uv run python scripts/build_swebench50_prebuilt.py \
        [--repos flask,requests,pytest,sphinx] [--limit N] [--skip-validate]

Note: ``django`` and ``sympy`` use their own test runners (not ``pytest``) and are
handled separately; this builder's default validation only covers pytest-based
repos.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks" / "swebench50"
REPOS_DIR = TASKS_DIR / "repos"

# The conda environment name baked into every official sweb.eval image.
CONDA_ENV = "testbed"
ACTIVATE = f"source /opt/miniconda3/bin/activate {CONDA_ENV}"

# Host Clash proxy injected into containers so network-dependent tests (e.g.
# requests' httpbin fixtures) can reach the internet. Only applied to the repos
# whose tests need it.
HTTP_PROXY = "http://host.docker.internal:7890"
NETWORK_REPOS = {"requests"}

# Repos whose test suite runs under plain ``python -m pytest`` (the default).
# ``django`` / ``sympy`` need custom runners and are excluded from this builder.
PYTEST_REPOS = {"flask", "requests", "pytest", "sphinx", "matplotlib",
                "scikit-learn", "seaborn", "xarray", "astropy"}

# sympy runs its own ``bin/test`` runner; its node IDs are ``test_<name>`` and the
# keyword is the name with the ``test_`` prefix stripped.
SYMPY_REPOS = {"sympy"}

# django runs ``tests/runtests.py`` with DJANGO_SETTINGS_MODULE; its node IDs are
# ``test_name (module.Class)`` and map to ``module.Class.test_name``.
DJANGO_REPOS = {"django"}

_DJANGO_PAREN = re.compile(r"^(\S+) \((.+)\)$")


def node_to_cmd(repo: str, node: str) -> str:
    """Return the in-container command that locates a single test ``node``."""
    if repo in SYMPY_REPOS:
        return f"python bin/test -C --verbose -k {shlex.quote(node[5:])}"
    if repo in DJANGO_REPOS:
        m = _DJANGO_PAREN.match(node)
        label = f"{m.group(2)}.{m.group(1)}" if m else node
        return (
            "PYTHONPATH=/testbed DJANGO_SETTINGS_MODULE=tests.test_sqlite "
            f"python tests/runtests.py {shlex.quote(label)} --verbosity 0"
        )
    return f"python -m pytest {shlex.quote(node)} -q --no-header --tb=no"


def _as_list(x):
    if isinstance(x, str):
        return json.loads(x)
    return x


def _normalize_nodes(nodes: list[str]) -> list[str]:
    """Fix truncated parametrized node IDs (a SWE-bench dataset artifact).

    Some pass-to-pass node IDs were cut short when the dataset was collected
    (e.g. ``testing/test_assertrewrite.py::test_get_assertion_exprs[assert`` — the
    parametrization is missing its closing ``]``), so ``pytest`` cannot locate
    them. An unclosed ``[`` marks the truncation; strip the parametrization and
    run the base test (all its parametrizations) instead — safe for regression
    (P2P) tests, which must all pass on the buggy baseline regardless.
    """
    out: list[str] = []
    for node in nodes:
        lb = node.rfind("[")
        if lb != -1 and "]" not in node[lb:]:
            out.append(node[:lb])
        else:
            out.append(node)
    return out


def image_name(instance_id: str) -> str:
    """Map ``<owner>__<repo>-<issue>`` to the official prebuilt image name."""
    owner, rest = instance_id.split("__", 1)
    return f"swebench/sweb.eval.x86_64.{owner}_1776_{rest}"


def run(argv: list[str], *, timeout: int = 600, input: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout, input=input,
    )


def docker(*args: str, timeout: int = 1200) -> subprocess.CompletedProcess:
    return run(["docker", *args], timeout=timeout)


def ensure_image(image: str) -> None:
    """Pull ``image`` unless it is already present locally."""
    check = docker("image", "inspect", image)
    if check.returncode == 0:
        return
    proc = docker("pull", image, timeout=3600)
    if proc.returncode != 0:
        raise RuntimeError(f"pull failed: {(proc.stderr or proc.stdout).strip()[:300]}")


def extract_testbed(image: str, dest: Path) -> None:
    """Copy the image's ``/testbed`` tree out to ``dest`` (idempotent)."""
    if (dest / ".git").exists():
        return
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    created = docker("create", image)
    if created.returncode != 0:
        raise RuntimeError(f"docker create failed: {created.stderr.strip()[:300]}")
    cid = created.stdout.strip()
    try:
        cp = docker("cp", f"{cid}:/testbed/.", str(dest))
        if cp.returncode != 0:
            raise RuntimeError(f"docker cp failed: {cp.stderr.strip()[:300]}")
    finally:
        docker("rm", "-f", cid)


def _git_apply(dest: Path, patch: str, *, reverse: bool = False) -> subprocess.CompletedProcess:
    """Apply a unified diff to ``dest`` with ``git apply`` (bytes input).

    The patch is piped as UTF-8 *bytes* — not via ``text=True`` — because on
    Windows text-mode stdin translates ``\\n`` to ``\\r\\n``, which makes ``git
    apply`` reject the patch against an LF checkout ("patch does not apply").
    """
    argv = ["git", "-C", str(dest), "apply"]
    if reverse:
        argv.append("-R")
    argv.append("-")
    return subprocess.run(argv, input=patch.encode("utf-8"), capture_output=True, timeout=300)


def apply_test_patch(dest: Path, test_patch: str) -> None:
    if not test_patch.strip():
        return
    proc = _git_apply(dest, test_patch)
    if proc.returncode != 0:
        raise RuntimeError(f"test_patch apply failed: {proc.stderr.decode('utf-8', 'replace').strip()[:300]}")


def _run_node(runtime, repo: str, node: str, timeout: float = 300.0) -> bool:
    """Run a single test node with the repo's own runner; True if it passed."""
    result = runtime.run_command_sync(node_to_cmd(repo, node), timeout=timeout)
    return result["returncode"] == 0


def validate(image: str, dest: Path, repo: str, ftp: list[str], ptp: list[str], gold_patch: str) -> dict:
    """Double-directional check inside the image's conda env.

    Returns a dict of ``{ftp_buggy_fails, ptp_buggy_passes, fixed_all_pass}``.
    """
    from minicodex.runtime.sandbox.docker import DockerRuntime

    runtime = DockerRuntime(
        image=image, mount_path=dest, cwd="/testbed", activate_cmd=ACTIVATE,
        http_proxy=HTTP_PROXY if repo in NETWORK_REPOS else "",
    )
    try:
        # F2P is small (a handful of tests) and must each fail individually, so
        # run per-node. P2P is large for pytest repos — batch it into a single
        # invocation; sympy's `bin/test` is fast, so run its P2P per-node too.
        ftp_buggy = {n: _run_node(runtime, repo, n) for n in ftp}
        if repo in PYTEST_REPOS:
            ptp_buggy_ok = runtime.run_pytest_batch(ptp, timeout=300)
        else:
            ptp_buggy_ok = all(_run_node(runtime, repo, n) for n in ptp)

        # Apply the gold patch on the host (visible via the bind mount).
        _git_apply(dest, gold_patch)
        ftp_fixed_ok = all(_run_node(runtime, repo, n) for n in ftp)
        if repo in PYTEST_REPOS:
            ptp_fixed_ok = runtime.run_pytest_batch(ptp, timeout=300)
        else:
            ptp_fixed_ok = all(_run_node(runtime, repo, n) for n in ptp)
        # Revert the gold patch, keeping the buggy baseline + test_patch.
        _git_apply(dest, gold_patch, reverse=True)
    finally:
        runtime.cleanup()

    return {
        "ftp_buggy_fails": all(not passed for passed in ftp_buggy.values()),
        "ptp_buggy_passes": ptp_buggy_ok,
        "fixed_all_pass": ftp_fixed_ok and ptp_fixed_ok,
    }


def build_one(entry: dict, *, validate_enabled: bool) -> dict:
    iid = entry["instance_id"]
    image = image_name(iid)
    ftp = _as_list(entry["FAIL_TO_PASS"])
    # Normalize P2P node IDs (strip truncated parametrizations) so pytest can
    # locate the regression tests the SWE-bench dataset truncated.
    ptp = _normalize_nodes(_as_list(entry["PASS_TO_PASS"]))
    dest = REPOS_DIR / iid

    ensure_image(image)
    extract_testbed(image, dest)
    apply_test_patch(dest, entry["test_patch"])

    valid = None
    if validate_enabled:
        repo_key = entry["repo"].split("/")[0]
        valid = validate(image, dest, repo_key, ftp, ptp, entry["patch"])

    record = {
        "instance_id": iid,
        "repo": entry["repo"],
        "base_commit": entry["base_commit"],
        "problem_statement": entry["problem_statement"],
        "patch": entry["patch"],
        "test_patch": entry["test_patch"],
        "FAIL_TO_PASS": ftp,
        "PASS_TO_PASS": ptp,
        "test_command": "pytest -q",
        "repo_path": str(dest),
        "docker_image": image,
    }
    (TASKS_DIR / f"{iid}.jsonl").write_text(
        json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return {"id": iid, "image": image, "valid": valid}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repos", default=None,
                        help="Comma-separated repo names to build (default: pytest-based repos).")
    parser.add_argument("--limit", type=int, default=0, help="Max instances to build (0 = all).")
    parser.add_argument("--skip-validate", action="store_true",
                        help="Skip the double-directional validation (faster, records only).")
    parser.add_argument("--include-django-sympy", action="store_true",
                        help="Also build django/sympy (no pytest validation for those).")
    args = parser.parse_args()

    records = json.loads((ROOT / "swebench_50.json").read_text(encoding="utf-8"))
    wanted = [r.strip() for r in (args.repos or "").split(",") if r.strip()] or list(PYTEST_REPOS)
    if args.include_django_sympy:
        wanted += ["django", "sympy"]

    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    REPOS_DIR.mkdir(parents=True, exist_ok=True)

    done = 0
    ok = 0
    for entry in records:
        iid = entry["instance_id"]
        repo_key = _repo_key(iid)
        if repo_key not in wanted:
            continue
        if args.limit and done >= args.limit:
            break
        done += 1
        validate_enabled = args.skip_validate is False and (
            repo_key in PYTEST_REPOS or repo_key in SYMPY_REPOS or repo_key in DJANGO_REPOS
        )
        try:
            result = build_one(entry, validate_enabled=validate_enabled)
            valid = result["valid"]
            status = ""
            if valid is not None:
                okv = all(valid.values())
                ok += int(okv)
                status = "OK" if okv else f"INVALID {valid}"
            else:
                status = "SKIPPED-VALIDATE"
            print(f"[{status}] {result['id']}  {result['image']}")
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"[ERROR] {iid}: {type(exc).__name__}: {exc}")

    print(f"\nBuilt {done} instances; {ok} validated OK -> {TASKS_DIR}")
    return 0


def _repo_key(instance_id: str) -> str:
    """Extract the repo key from ``<owner>__<repo>-<issue>``.

    ``<repo>`` may itself contain dashes (``scikit-learn``, ``pytest-dev``), so the
    issue number is the trailing ``-<digits>`` segment.
    """
    rest = instance_id.split("__", 1)[1]
    base = rest.rsplit("-", 1)[0]
    return base


if __name__ == "__main__":
    raise SystemExit(main())
