"""Quality lock for the production task set.

Guards the hand-built repo-level task set (``tasks/``) against regressions. The
assertions mirror the SWE-bench contract:

  * 40 <= N <= 80 tasks
  * unique task ids
  * all three difficulty tiers (easy / medium / hard) present
  * every task has a non-empty ``fail_to_pass`` AND ``pass_to_pass``
  * every task verifies double-directionally: on the buggy baseline every
    ``fail_to_pass`` test fails and every ``pass_to_pass`` test passes, and after
    applying ``gold_patch`` every one of them passes.
"""

from pathlib import Path

from minicodex.eval.task import load_tasks
from minicodex.eval.verification import verify_gold_patch

TASKS_DIR = Path(__file__).resolve().parents[2] / "tasks"


def _load():
    return load_tasks(TASKS_DIR)


def test_task_count_within_bounds():
    tasks = _load()
    assert 40 <= len(tasks) <= 80, f"expected 40-80 tasks, got {len(tasks)}"


def test_task_ids_are_unique():
    ids = [t.id for t in _load()]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    assert not dupes, f"duplicate task ids: {dupes}"


def test_all_difficulty_tiers_present():
    difficulties = {t.metadata.get("difficulty") for t in _load()}
    assert {"easy", "medium", "hard"} <= difficulties, f"missing tiers in {difficulties}"


def test_every_task_has_fail_to_pass():
    missing = [t.id for t in _load() if not t.fail_to_pass]
    assert not missing, f"tasks without fail_to_pass: {missing}"


def test_every_task_has_pass_to_pass():
    missing = [t.id for t in _load() if not t.pass_to_pass]
    assert not missing, f"tasks without pass_to_pass: {missing}"


def test_every_task_verifies_double_directionally():
    failures = []
    for t in _load():
        result = verify_gold_patch(t)
        if not result.ok:
            failures.append((t.id, result.failures))
    assert not failures, f"tasks failing double-directional verification: {failures}"
