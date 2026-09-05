"""Repo spec: a data pipeline with a cross-module transform bug."""

REPO = "pipeline"

FILES = {
    "pipeline/__init__.py": "",
    "pipeline/io.py": '''"""IO: read lines from a file."""


def read_lines(path: str) -> list[str]:
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]
''',
    "pipeline/transform.py": '''"""Transform: uppercase each line."""


def transform(line: str) -> str:
    return line.upper()
''',
    "pipeline/pipeline.py": '''"""Pipeline: read -> transform -> write."""

from pipeline.io import read_lines
from pipeline.transform import transform


def run(in_path: str, out_path: str) -> int:
    lines = read_lines(in_path)
    out = [transform(l) for l in lines]
    with open(out_path, "w") as f:
        for l in out:
            f.write(l + "\\n")
    return len(out)
''',
}

TESTS = {
    "tests/test_pipeline.py": '''"""Tests for pipeline (transform bug surfaces via output)."""

from pipeline.pipeline import run


def test_pipeline_uppercases():
    with open("in.txt", "w") as f:
        f.write("hello\\nworld\\n")
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
''',
}

TASKS = [
    {
        "id": "pipeline-transform",
        "instruction": (
            "Fix the bug in the data pipeline where the transformed output is "
            "wrong. The test 'test_pipeline_uppercases' fails because the "
            "output isn't uppercased. Find the root cause."
        ),
        "difficulty": "hard",
        "category": "cross-module",
        "lines": 1,
        "bug": [
            ("pipeline/transform.py",
             "    return line.upper()\n",
             "    return line.lower()\n"),
        ],
        "fail_to_pass": [
            "tests/test_pipeline.py::test_pipeline_uppercases",
        ],
        "pass_to_pass": [
            "tests/test_pipeline.py::test_pipeline_empty_input",
        ],
    },
]
