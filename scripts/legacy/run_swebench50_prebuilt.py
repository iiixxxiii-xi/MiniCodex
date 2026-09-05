"""Run the SWE-bench50 subset (official pre-built images) through the agent.

Feeds the ``tasks/swebench50/*.jsonl`` records to the eval runner. Each record
carries ``repo_path`` (the extracted ``/testbed`` checkout with ``test_patch``
applied) and ``docker_image`` (the official ``swebench/sweb.eval.*`` image). The
runner mounts the checkout back over ``/testbed`` inside the image and activates
the image's ``testbed`` conda env before every shell/test command, so the model
solves against the exact SWE-bench environment.

Usage::

    uv run python scripts/run_swebench50_prebuilt.py \
        [--model deepseek-v4-flash] [--step-limit 30] [--limit N] \
        [--verify] [--output results/swebench50]

Every instance is run once; a summary is written to ``summary.json``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from minicodex.eval.runner import Runner
from minicodex.eval.swebench import parse_swebench_jsonl
from minicodex.model.openai import OpenAIModel

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks" / "swebench50"
DEFAULT_OUTPUT = ROOT / "results" / "swebench50"

CONDA_ENV = "testbed"
ACTIVATE = f"source /opt/miniconda3/bin/activate {CONDA_ENV}"
CONTAINER_CWD = "/testbed"


def build_model(model_id: str):
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise SystemExit("DEEPSEEK_API_KEY is not set in .env; cannot run a real model.")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    is_v4 = "v4" in model_id
    # Keep the reasoning model's thinking ON. The loop echoes reasoning_content
    # back on the follow-up request, so multi-turn tool use no longer 400s.
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


async def run_one(task, model, output_dir: Path, step_limit: int, verify: bool):
    image = task.metadata.get("docker_image")
    if not image:
        return None
    runner = Runner(
        model,
        output_dir=output_dir,
        step_limit=step_limit,
        sandbox="docker",
        docker_image=image,
        container_cwd=CONTAINER_CWD,
        activate_cmd=ACTIVATE,
        verify=verify,
        context_policy="compaction" if verify else "none",
    )
    return await runner.run(task)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--step-limit", type=int, default=30)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    tasks = load_tasks(args.limit)
    if not tasks:
        print(f"error: no tasks in {TASKS_DIR}", file=sys.stderr)
        return 1

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    model = build_model(args.model)

    print(f"Running {len(tasks)} SWE-bench50 task(s) with model={args.model} verify={args.verify}...")
    results = []
    for task in tasks:
        print(f"\n=== {task.id} ===")
        result = await run_one(task, model, output_dir, args.step_limit, args.verify)
        if result is None:
            continue
        results.append(result)
        verdict = "PASS" if result.passed else "FAIL"
        print(
            f"{verdict} {result.task_id}  exit={result.exit_status}  "
            f"tool_calls={result.metrics.tool_calls}  cost=${result.metrics.cost_usd:.4f}"
        )
        if result.error:
            print(f"  error: {result.error[:500]}")

    summary = [r.model_dump(mode="json") for r in results]
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    passed = sum(1 for r in results if r.passed)
    print(f"\nDone: {passed}/{len(results)} passed. Results in {output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
