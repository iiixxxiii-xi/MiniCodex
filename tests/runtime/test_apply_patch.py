import subprocess

from minicodex.runtime.tools.apply_patch import run


def _git(tmp_path, *args):
    subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True, text=True)


def _init_repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "T")
    (tmp_path / "a.txt").write_text("hello\n", encoding="utf-8")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-q", "-m", "init")


PATCH = """--- a/a.txt
+++ b/a.txt
@@ -1 +1 @@
-hello
+world
"""


def test_apply_patch_success(tmp_path):
    _init_repo(tmp_path)
    result = run({"patch": PATCH}, cwd=tmp_path)
    assert result["returncode"] == 0
    assert result["error"] == ""
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "world\n"


def test_apply_patch_conflict_returns_error(tmp_path):
    _init_repo(tmp_path)
    bad = """--- a/a.txt
+++ b/a.txt
@@ -1 +1 @@
-does-not-match
+world
"""
    result = run({"patch": bad}, cwd=tmp_path)
    assert result["returncode"] != 0
    assert result["error"]
    assert result["retryable"] is False
    # file left unchanged
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "hello\n"


def test_apply_patch_missing_patch_arg(tmp_path):
    result = run({}, cwd=tmp_path)
    assert result["returncode"] != 0
    assert result["retryable"] is False


CLAUDE_PATCH = """*** Begin Patch
*** Update File: a.txt
@@
-hello
+world
*** End Patch"""


def test_apply_patch_claude_format(tmp_path):
    """The fuzzy applier must handle Claude's ``*** Update File`` format,
    whose hunk header is a bare ``@@`` (no line numbers)."""
    _init_repo(tmp_path)
    result = run({"patch": CLAUDE_PATCH}, cwd=tmp_path)
    assert result["returncode"] == 0, result["error"]
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "world\n"


def test_apply_patch_claude_insertion(tmp_path):
    """A context hunk (no ``-`` lines) inserts the ``+`` lines at the right spot."""
    _init_repo(tmp_path)
    patch = (
        "*** Begin Patch\n"
        "*** Update File: a.txt\n"
        "@@\n"
        "hello\n"
        "+inserted\n"
        "*** End Patch"
    )
    result = run({"patch": patch}, cwd=tmp_path)
    assert result["returncode"] == 0, result["error"]
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "hello\ninserted\n"
