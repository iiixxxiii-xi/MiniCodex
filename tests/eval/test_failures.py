"""Failure trajectories are bucketed by reason and kept replayable."""

from minicodex.eval.failures import collect_failures
from minicodex.eval.runner import RunResult


def _result(task_id, exit_status, passed, trajectory_path=None, error=""):
    return RunResult(
        task_id=task_id,
        exit_status=exit_status,
        passed=passed,
        trajectory_path=trajectory_path,
        error=error,
    )


def test_collect_failures_groups_by_exit_status():
    results = [
        _result("a", "ModelError", False, "traj/a.jsonl"),
        _result("b", "ModelError", False, "traj/b.jsonl"),
        _result("c", "LimitsExceeded", False, "traj/c.jsonl"),
        _result("d", "RepeatedFormatError", False, "traj/d.jsonl"),
        _result("e", "Error", False, "traj/e.jsonl"),
        _result("f", "finished", True, "traj/f.jsonl"),  # passed -> excluded
    ]
    coll = collect_failures(results)
    assert coll.total_failures == 5
    by_status = {c.exit_status: c for c in coll.categories}
    assert set(by_status) == {"ModelError", "LimitsExceeded", "RepeatedFormatError", "Error"}
    assert by_status["ModelError"].count == 2
    assert by_status["ModelError"].trajectory_paths == ["traj/a.jsonl", "traj/b.jsonl"]
    assert by_status["LimitsExceeded"].count == 1
    assert by_status["RepeatedFormatError"].count == 1
    assert by_status["Error"].count == 1


def test_collect_failures_classifies_test_failure_and_timeout():
    results = [
        _result("t1", "finished", False, "traj/t1.jsonl", error="hidden test timed out after 120s"),
        _result("t2", "finished", False, "traj/t2.jsonl", error="assertion failed"),
    ]
    coll = collect_failures(results)
    by_status = {c.exit_status: c for c in coll.categories}
    assert "timeout" in by_status
    assert by_status["timeout"].count == 1
    assert by_status["timeout"].trajectory_paths == ["traj/t1.jsonl"]
    assert "TestFailed" in by_status
    assert by_status["TestFailed"].count == 1
    assert by_status["TestFailed"].trajectory_paths == ["traj/t2.jsonl"]


def test_collect_failures_empty_when_all_pass():
    results = [_result("a", "finished", True), _result("b", "finished", True)]
    coll = collect_failures(results)
    assert coll.total_failures == 0
    assert coll.categories == []


def test_collect_failures_skips_missing_trajectory_paths():
    results = [_result("a", "ModelError", False, None)]
    coll = collect_failures(results)
    cat = coll.categories[0]
    assert cat.count == 1
    assert cat.trajectory_paths == []
