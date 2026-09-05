"""Tests for fs (permission bug surfaces via write)."""

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
