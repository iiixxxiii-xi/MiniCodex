"""Tests for pipeline (transform bug surfaces via output)."""

from pipeline.pipeline import run


def test_pipeline_uppercases():
    with open("in.txt", "w") as f:
        f.write("hello\nworld\n")
    n = run("in.txt", "out.txt")
    with open("out.txt") as f:
        content = f.read()
    assert "HELLO" in content
    assert "WORLD" in content
    assert n == 2


def test_pipeline_empty_input():
    with open("in.txt", "w") as f:
        f.write("")
    n = run("in.txt", "out.txt")
    assert n == 0
