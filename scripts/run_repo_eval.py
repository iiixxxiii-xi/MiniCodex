"""Run the repo-level task set through a real model and report the pass rate.

Unlike ``minicodex eval`` (ablation), this drives the runner directly against
*throwaway copies* of each task's workspace, so the committed ``tasks/repos/``
buggy baseline is never mutated by the agent's patch. It also bounds each run
with ``--step-limit`` so a weak model can't loop unbounded on hard tasks.

Usage::

    uv run python scripts/run_repo_eval.py --model deepseek-chat \
        --output results/repo-upgrade --step-limit 25 --concurrency 4
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from minicodex.eval.runner import Runner
from minicodex.eval.task import load_tasks
from minicodex.model.openai import OpenAIModel

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TASKS = ROOT / "tasks"
DEFAULT_OUTPUT = ROOT / "results" / "repo-upgrade"


def build_model(model_id: str):
    import os

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise SystemExit("DEEPSEEK_API_KEY is not set in .env; cannot run a real model.")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    is_v4 = "v4" in model_id
    return OpenAIModel(
        model=model_id,
        base_url=base_url,
        api_key=api_key,
        max_tokens=8192 if is_v4 else 4096,
        extra_body={"thinking": {"type": "enabled"}} if is_v4 else None,
    )


async def run_one(task, model, workdir: Path, output_dir: Path, step_limit: int, sem):
    async with sem:
        # Throwaway copy so the committed buggy baseline is never mutated.
        src = Path(task.repo_path)
        dst = workdir / task.repo / task.id
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, dirs_exist_ok=True)
        task.repo_path = str(dst.resolve())

        runner = Runner(model, output_dir=output_dir, step_limit=step_limit, sandbox="local")
        return await runner.run(task)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default=str(DEFAULT_TASKS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--step-limit", type=int, default=25)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0, help="run only the first N tasks (0 = all)")
    args = parser.parse_args()

    tasks = load_tasks(Path(args.tasks))
    if args.limit:
        tasks = tasks[: args.limit]
    if not tasks:
        raise SystemExit("no tasks found")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    model = build_model(args.model)

    with tempfile.TemporaryDirectory(prefix="minicodex-repo-eval-") as td:
        workdir = Path(td)
        sem = asyncio.Semaphore(args.concurrency)
        print(f"Running {len(tasks)} task(s) with model={args.model} (concurrency={args.concurrency})...")
        results = await asyncio.gather(
            *(run_one(t, model, workdir, output_dir, args.step_limit, sem) for t in tasks)
        )

    summary = [r.model_dump(mode="json") for r in results]
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    passed = sum(1 for r in results if r.passed)
    for r in results:
        verdict = "PASS" if r.passed else "FAIL"
        print(f"{verdict} {r.task_id}  exit={r.exit_status}  tool_calls={r.metrics.tool_calls}")
    print(f"\nDone: {passed}/{len(results)} passed ({passed / len(results):.1%}). Results in {output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
