"""Task model and loader tests: defaults, roundtrip, and explicit failure paths."""

import json

import pytest

from minicodex.eval.task import Task, load_task, load_tasks


def test_task_defaults():
    t = Task(id="t1", repo="demo", instruction="do the thing")
    assert t.gold_patch == ""
    assert t.test_command == ""
    assert t.repo_path is None
    assert t.base_commit == ""
    assert t.metadata == {}
    assert t.fail_to_pass == []
    assert t.pass_to_pass == []


def test_task_fail_pass_roundtrip_from_dict():
    t = Task.from_dict(
        {
            "id": "t1",
            "repo": "demo",
            "instruction": "fix the bug",
            "fail_to_pass": ["tests/test_demo.py::test_a", "tests/test_demo.py::test_b"],
            "pass_to_pass": ["tests/test_demo.py::test_c"],
        }
    )
    assert t.fail_to_pass == ["tests/test_demo.py::test_a", "tests/test_demo.py::test_b"]
    assert t.pass_to_pass == ["tests/test_demo.py::test_c"]


def test_task_fail_pass_lists_are_isolated():
    # Mutating one instance's list must not leak into another instance.
    t1 = Task.from_dict({"id": "t1", "repo": "demo", "instruction": "x", "fail_to_pass": ["a"]})
    t2 = Task.from_dict({"id": "t2", "repo": "demo", "instruction": "y"})
    t1.fail_to_pass.append("b")
    assert t2.fail_to_pass == []


def test_task_roundtrip_from_dict():
    t = Task.from_dict(
        {
            "id": "t1",
            "repo": "demo",
            "instruction": "fix the bug",
            "gold_patch": "diff --git a/x b/x",
            "test_command": "pytest -q",
            "repo_path": "/tmp/demo",
        }
    )
    assert t.gold_patch == "diff --git a/x b/x"
    assert t.test_command == "pytest -q"
    assert t.repo_path == "/tmp/demo"


def test_task_ignores_unknown_fields():
    t = Task.from_dict({"id": "t1", "repo": "demo", "instruction": "x", "FAIL_TO_PASS": ["a"]})
    assert t.id == "t1"


def test_task_requires_id():
    with pytest.raises(ValueError):
        Task.from_dict({"repo": "demo", "instruction": "x"})


def test_load_task_roundtrip(tmp_path):
    path = tmp_path / "task.json"
    path.write_text(
        json.dumps({"id": "t1", "repo": "demo", "instruction": "x", "test_command": "pytest -q"}),
        encoding="utf-8",
    )
    t = load_task(path)
    assert isinstance(t, Task)
    assert t.id == "t1"
    assert t.test_command == "pytest -q"


def test_load_task_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_task(tmp_path / "nope.json")


def test_load_task_malformed_json_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        load_task(path)


def test_load_tasks_from_directory_sorted(tmp_path):
    (tmp_path / "b.json").write_text(json.dumps({"id": "b", "repo": "r", "instruction": "x"}), encoding="utf-8")
    (tmp_path / "a.json").write_text(json.dumps({"id": "a", "repo": "r", "instruction": "x"}), encoding="utf-8")
    tasks = load_tasks(tmp_path)
    assert [t.id for t in tasks] == ["a", "b"]


def test_load_tasks_empty_directory(tmp_path):
    assert load_tasks(tmp_path) == []


def test_load_tasks_single_jsonl_file(tmp_path):
    path = tmp_path / "tasks.jsonl"
    path.write_text(
        json.dumps({"id": "t1", "repo": "r", "instruction": "x"}) + "\n"
        + json.dumps({"id": "t2", "repo": "r", "instruction": "y"}) + "\n",
        encoding="utf-8",
    )
    tasks = load_tasks(path)
    assert [t.id for t in tasks] == ["t1", "t2"]
