"""SWE-bench local JSONL parsing -> Task, without any HuggingFace dependency."""

import json

import pytest

from minicodex.eval.swebench import parse_swebench_jsonl, to_task


def _record(**overrides):
    rec = {
        "instance_id": "astropy__astropy-12907",
        "repo": "astropy/astropy",
        "problem_statement": "Fix the coordinate transform bug.",
        "patch": "diff --git a/x b/x",
        "base_commit": "abc123",
        "FAIL_TO_PASS": ["test_coord[0]"],
        "PASS_TO_PASS": ["test_coord[1]"],
    }
    rec.update(overrides)
    return rec


def test_to_task_maps_fields():
    task = to_task(_record())
    assert task.id == "astropy__astropy-12907"
    assert task.repo == "astropy/astropy"
    assert task.instruction == "Fix the coordinate transform bug."
    assert task.gold_patch == "diff --git a/x b/x"
    assert task.base_commit == "abc123"
    assert task.fail_to_pass == ["test_coord[0]"]
    assert task.pass_to_pass == ["test_coord[1]"]
    # FAIL_TO_PASS / PASS_TO_PASS are mapped onto the first-class fields and
    # must not linger in metadata.
    assert "FAIL_TO_PASS" not in task.metadata
    assert "PASS_TO_PASS" not in task.metadata


def test_to_task_defaults_missing_fail_pass():
    task = to_task({"id": "custom-1", "repo": "a/b", "instruction": "x"})
    assert task.fail_to_pass == []
    assert task.pass_to_pass == []


def test_to_task_requires_instance_id():
    with pytest.raises(ValueError):
        to_task({"repo": "a/b", "problem_statement": "x"})


def test_to_task_accepts_id_alias():
    task = to_task({"id": "custom-1", "repo": "a/b", "instruction": "x"})
    assert task.id == "custom-1"
    assert task.instruction == "x"


def test_parse_swebench_jsonl(tmp_path):
    path = tmp_path / "swe.jsonl"
    path.write_text(
        json.dumps(_record()) + "\n"
        + "this is not json\n"
        + json.dumps(_record(instance_id="django__django-1", repo="django/django")) + "\n",
        encoding="utf-8",
    )
    tasks = parse_swebench_jsonl(path)
    assert [t.id for t in tasks] == ["astropy__astropy-12907", "django__django-1"]


def test_parse_swebench_skips_invalid_records(tmp_path):
    path = tmp_path / "swe.jsonl"
    path.write_text(
        json.dumps({"repo": "no-instance", "problem_statement": "x"}) + "\n"
        + json.dumps(_record()) + "\n",
        encoding="utf-8",
    )
    tasks = parse_swebench_jsonl(path)
    assert len(tasks) == 1
    assert tasks[0].id == "astropy__astropy-12907"


def test_parse_swebench_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_swebench_jsonl(tmp_path / "nope.jsonl")
