from pathlib import Path

from minicodex.context.file_reference import offload, replace_if_large


def test_offload_writes_content_and_returns_reference(tmp_path):
    path = tmp_path / "big.txt"
    ref = offload("hello world", path)
    assert "big.txt" in ref
    assert path.read_text(encoding="utf-8") == "hello world"


def test_offload_creates_parent_dirs(tmp_path):
    path = tmp_path / "a" / "b" / "big.txt"
    offload("content", path)
    assert path.exists()


def test_replace_if_large_short_text_unchanged(tmp_path):
    path = tmp_path / "small.txt"
    out = replace_if_large("short", path, max_len=100)
    assert out == "short"
    assert not path.exists()


def test_replace_if_large_offloads_large_text(tmp_path):
    path = tmp_path / "large.txt"
    content = "x" * 50
    out = replace_if_large(content, path, max_len=10)
    assert out != content
    assert "large.txt" in out
    assert path.read_text(encoding="utf-8") == content  # raw preserved on disk
