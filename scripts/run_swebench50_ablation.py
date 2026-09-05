"""Run the SWE-bench50 subset under the four harness presets (ablation).

The four arms isolate which runtime primitive still matters once the model is
strong, answering "which Runtime primitive is indispensable even after model
capability grows":

  - ``minimal``       bare ReAct loop + ``test_runner`` (no context policy, no
                      completion verification, no retry requery)
  - ``context``       minimal + context compaction (summarize-and-offload)
  - ``verification``  minimal + post-patch completion verifier (run regression
                      tests on ``done``, re-query on failure)
  - ``complex``       context + verification + retry requery (everything on)

Each arm runs every task once inside its official pre-built image (``/testbed``
with the image's ``testbed`` conda env activated). Aggregated 6-metric summaries
per arm are written to ``summary.json``; per-task results to ``results/<arm>/``.

Usage::

    uv run python scripts/run_swebench50_ablation.py \
        [--model deepseek-v4-pro] [--step-limit 40] [--limit N] [--arms minimal,context]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from minicodex.eval.metrics import aggregate_metrics
from minicodex.eval.runner import Runner
from minicodex.eval.swebench import parse_swebench_jsonl
from minicodex.model.openai import OpenAIModel

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks" / "swebench50"
DEFAULT_OUTPUT = ROOT / "results" / "swebench50-ablation"

CONDA_ENV = "testbed"
ACTIVATE = f"source /opt/miniconda3/bin/activate {CONDA_ENV}"
CONTAINER_CWD = "/testbed"

# Two complementary ablations:
#   (1) the 4-way harness comparison — complex vs minimal vs +context vs
#       +verification (the research question's headline);
#   (2) the per-dimension policy comparison — which *policy* within context /
#       tool / retry does best ("比较不同 context/tool/retry policy").
# Every arm varies exactly one knob against "minimal" (except "complex").
PRESETS: dict[str, dict] = {
    # -- 4-way harness comparison -----------------------------------------
    "minimal": dict(context_policy="none", verify=False, max_requeries=0, retry_policy="none", tool_policy="all"),
    "context": dict(context_policy="compaction", verify=False, max_requeries=0, retry_policy="none", tool_policy="all"),
    "verification": dict(context_policy="none", verify=True, max_requeries=0, retry_policy="none", tool_policy="all"),
    "complex": dict(context_policy="compaction", verify=True, max_requeries=3, retry_policy="fixed", tool_policy="all"),
    # -- context policy dimension ------------------------------------------
    "ctx_sliding": dict(context_policy="sliding", verify=False, max_requeries=0, retry_policy="none", tool_policy="all"),
    "ctx_truncation": dict(context_policy="truncation", verify=False, max_requeries=0, retry_policy="none", tool_policy="all"),
    # -- tool policy dimension ---------------------------------------------
    "tool_no_test_runner": dict(context_policy="none", verify=False, max_requeries=0, retry_policy="none", tool_policy="no_test_runner"),
    # -- retry policy dimension --------------------------------------------
    "retry_fixed": dict(context_policy="none", verify=False, max_requeries=3, retry_policy="fixed", tool_policy="all"),
    "retry_backoff": dict(context_policy="none", verify=False, max_requeries=3, retry_policy="backoff", tool_policy="all"),
}


def build_model(model_id: str):
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise SystemExit("DEEPSEEK_API_KEY is not set in .env; cannot run a real model.")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    is_v4 = "v4" in model_id
    return OpenAIModel(
        model=model_id,
        base_url=base_url,
        api_key=api_key,
        max_tokens=8192,
        extra_body={"thinking": {"type": "enabled"}} if is_v4 else None,
    )


def load_tasks(limit: int = 0) -> list:
    tasks = []
    for jl in sorted(TASKS_DIR.glob("*.jsonl")):
        for task in parse_swebench_jsonl(jl):
            md = task.metadata
            repo_path = md.get("repo_path")
            if not repo_path or not Path(repo_path).exists():
                print(f"skip {task.id}: no repo_path checkout", file=sys.stderr)
                continue
            task.repo_path = repo_path
            tasks.append(task)
    if limit:
        tasks = tasks[:limit]
    return tasks


async def run_arm(name: str, preset: dict, tasks, model, output_dir: Path, step_limit: int, concurrency: int):
    arm_dir = output_dir / name
    arm_dir.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _run_one(task):
        image = task.metadata.get("docker_image")
        if not image:
            return None
        async with semaphore:
            runner = Runner(
                model,
                output_dir=arm_dir,
                step_limit=step_limit,
                sandbox="docker",
                docker_image=image,
                container_cwd=CONTAINER_CWD,
                activate_cmd=ACTIVATE,
                context_policy=preset["context_policy"],
                verify=preset["verify"],
                max_requeries=preset["max_requeries"],
                retry_policy=preset["retry_policy"],
                tool_policy=preset["tool_policy"],
            )
            result = await runner.run(task)
            verdict = "PASS" if result.passed else "FAIL"
            print(
                f"  [{name}] {verdict} {result.task_id}  exit={result.exit_status}  "
                f"tool_calls={result.metrics.tool_calls}  cost=${result.metrics.cost_usd:.4f}"
            )
            return result

    results = await asyncio.gather(*(_run_one(t) for t in tasks))
    return [r for r in results if r is not None]


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="deepseek-v4-pro")
    parser.add_argument("--step-limit", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=8, help="Tasks to run in parallel within an arm.")
    parser.add_argument("--limit", type=int, default=0, help="Max tasks to run (0 = all).")
    parser.add_argument("--arms", default="minimal,context,verification,complex",
                        help="Comma-separated preset names to run.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    tasks = load_tasks(args.limit)
    if not tasks:
        print(f"error: no tasks in {TASKS_DIR}", file=sys.stderr)
        return 1

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = [a for a in arms if a not in PRESETS]
    if unknown:
        print(f"error: unknown arms {unknown}; valid: {list(PRESETS)}", file=sys.stderr)
        return 1

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    model = build_model(args.model)

    print(f"Running {len(tasks)} task(s) x {len(arms)} arm(s) with model={args.model} "
          f"step_limit={args.step_limit}")
    summary: dict[str, dict] = {}
    for name in arms:
        print(f"\n=== arm: {name} ===")
        results = await run_arm(name, PRESETS[name], tasks, model, output_dir, args.step_limit, args.concurrency)
        metrics = aggregate_metrics([r.metrics for r in results])
        summary[name] = {
            "n_tasks": metrics.n_tasks,
            "success_rate": round(metrics.success_rate, 4),
            "success_count": sum(1 for r in results if r.passed),
            "avg_tool_calls": round(metrics.avg_tool_calls, 2),
            "avg_cost_usd": round(metrics.avg_cost_usd, 4),
            "avg_latency_ms": round(metrics.avg_latency_ms, 1),
            "avg_recovery_rate": round(metrics.avg_recovery_rate, 4),
            "avg_invalid_tool_call_rate": round(metrics.avg_invalid_tool_call_rate, 4),
        }
        print(f"  => {summary[name]}")

    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nSummary written to {output_dir / 'summary.json'}")
    for name, s in summary.items():
        print(f"  {name:14s} success={s['success_count']}/{s['n_tasks']} ({s['success_rate']:.1%}) "
              f"tool_calls={s['avg_tool_calls']} cost=${s['avg_cost_usd']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
