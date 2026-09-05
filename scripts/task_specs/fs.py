"""Repo spec: a filesystem with a cross-module permission bug."""

REPO = "fs"

FILES = {
    "fs/__init__.py": "",
    "fs/permissions.py": '''"""Permissions: check whether a user may access a path."""


def can_read(user: str, mode: str) -> bool:
    return mode in ("r", "rw")


def can_write(user: str, mode: str) -> bool:
    return mode == "rw"
''',
    "fs/fs.py": '''"""FS: the public read/write API."""

from fs.permissions import can_read, can_write


class FileSystem:
    def __init__(self):
        self._files = {}

    def read(self, user: str, path: str, mode: str):
        if not can_read(user, mode):
            return None
        return self._files.get(path)

    def write(self, user: str, path: str, content: str, mode: str):
        if not can_write(user, mode):
            return False
        self._files[path] = content
        return True
''',
}

TESTS = {
    "tests/test_fs.py": '''"""Tests for fs (permission bug surfaces via write)."""

from fs.fs import FileSystem


def test_write_readonly_denied():
    f = FileSystem()
    assert f.write("alice", "a.txt", "x", "r") is False


def test_write_rw_allowed():
    f = FileSystem()
    assert f.write("alice", "a.txt", "x", "rw") is True
    assert f.read("alice", "a.txt", "rw") == "x"


def test_read_denied():
    f = FileSystem()
    f.write("alice", "a.txt", "x", "rw")
    assert f.read("alice", "a.txt", "none") is None
''',
}

TASKS = [
    {
        "id": "fs-write-permission",
        "instruction": (
            "Fix the bug in the filesystem where a user with read-only access "
            "can still write files. The test 'test_write_readonly_denied' fails. "
            "Find the root cause."
        ),
        "difficulty": "hard",
        "category": "cross-module",
        "lines": 1,
        "bug": [
            ("fs/permissions.py",
             "    return mode == \"rw\"\n",
             "    return mode in (\"r\", \"rw\")\n"),
        ],
        "fail_to_pass": [
            "tests/test_fs.py::test_write_readonly_denied",
        ],
        "pass_to_pass": [
            "tests/test_fs.py::test_write_rw_allowed",
            "tests/test_fs.py::test_read_denied",
        ],
    },
]
