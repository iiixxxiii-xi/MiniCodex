"""Ablation runs the same task batch under different policy presets."""

import json

from minicodex.eval.ablation import (
    AblationPreset,
    AblationResult,
    DEFAULT_PRESETS,
    run_ablation,
)
from minicodex.eval.task import Task
from minicodex.model.mock import MockModel


def _make_task(task_id: str, tmp_path):
    return Task(
        id=task_id,
        repo="demo",
        instruction="do it",
        test_command='python -c "print(1)"',
        repo_path=str(tmp_path / task_id),
    )


def test_default_presets_cover_minimal_and_full():
    assert "minimal" in DEFAULT_PRESETS
    assert "full" in DEFAULT_PRESETS
    assert DEFAULT_PRESETS["minimal"].max_requeries == 0
    assert DEFAULT_PRESETS["full"].max_requeries > 0


def test_default_presets_expose_independent_dimensions():
    # context / retry / tool policies are independently adjustable, not just
    # the two minimal/full presets.
    assert DEFAULT_PRESETS["full"].context_policy == "none"
    assert DEFAULT_PRESETS["full"].retry_policy == "fixed"
    context_presets = [
        name for name, p in DEFAULT_PRESETS.items() if p.context_policy != "none"
    ]
    retry_presets = [
        name for name, p in DEFAULT_PRESETS.items() if p.retry_policy != "fixed"
    ]
    tool_presets = [
        name for name, p in DEFAULT_PRESETS.items() if p.tool_policy != "all"
    ]
    assert context_presets
    assert retry_presets
    assert tool_presets
    # the three dimensions vary independently across the preset set
    assert "sliding" in DEFAULT_PRESETS
    assert "truncation" in DEFAULT_PRESETS
    assert "compaction" in DEFAULT_PRESETS
    assert "backoff" in DEFAULT_PRESETS
    assert "no_retry" in DEFAULT_PRESETS


async def test_run_ablation_produces_one_result_per_preset(tmp_path):
    tasks = [_make_task("t1", tmp_path), _make_task("t2", tmp_path)]
    model = MockModel(script=[{"tool_calls": []}])
    results = await run_ablation(tasks, model, presets=list(DEFAULT_PRESETS.values()))

    assert len(results) == len(DEFAULT_PRESETS)
    assert {r.preset for r in results} == set(DEFAULT_PRESETS)
    for r in results:
        assert isinstance(r, AblationResult)
        assert len(r.results) == 2
        assert r.metrics.n_tasks == 2


async def test_run_ablation_custom_presets(tmp_path):
    tasks = [_make_task("t1", tmp_path)]
    presets = [
        AblationPreset(name="a", step_limit=1, max_requeries=0),
        AblationPreset(name="b", step_limit=0, max_requeries=3),
    ]
    model = MockModel(script=[{"tool_calls": []}])
    results = await run_ablation(tasks, model, presets=presets)
    assert [r.preset for r in results] == ["a", "b"]


async def test_run_ablation_serializes_to_json(tmp_path):
    tasks = [_make_task("t1", tmp_path)]
    model = MockModel(script=[{"tool_calls": []}])
    results = await run_ablation(tasks, model, presets=list(DEFAULT_PRESETS.values()))
    for r in results:
        data = r.model_dump(mode="json")
        assert data["preset"] == r.preset
        assert data["metrics"]["n_tasks"] == 1
        # roundtrip
        reloaded = AblationResult.model_validate(json.loads(json.dumps(data)))
        assert reloaded.preset == r.preset
