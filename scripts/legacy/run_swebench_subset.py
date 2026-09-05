"""Run the SWE-bench subset through the agent inside a Docker sandbox.

Feeds the ``tasks/swebench/*.jsonl`` records (plus their locally checked-out
repos under ``tasks/swebench/repos/<instance_id>``) to the eval runner, using a
Docker sandbox per task and the DeepSeek model configured via ``.env``
(``DEEPSEEK_API_KEY`` / ``DEEPSEEK_BASE_URL``).

Usage::

    uv run python scripts/run_swebench_subset.py [--tasks tasks/swebench] \
        [--output results/swebench-subset] [--model deepseek-chat] \
        [--step-limit 25] [--image minicodex-swebench:latest]

Every network/docker call carries a timeout; the daemon is probed first and a
clear error is raised (with a ``--sandbox local`` hint) rather than crashing.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from minicodex.eval.runner import RunResult, Runner
from minicodex.eval.swebench import parse_swebench_jsonl
from minicodex.eval.task import Task
from minicodex.model.openai import OpenAIModel
from minicodex.runtime.sandbox.docker import DockerError, DockerRuntime, docker_available

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TASKS = ROOT / "tasks" / "swebench"
DEFAULT_REPOS = ROOT / "tasks" / "swebench" / "repos"
DEFAULT_OUTPUT = ROOT / "results" / "swebench-subset"
DEFAULT_IMAGE = "minicodex-swebench:latest"

# Extra pytest install as a safety net if the image lacks it (idempotent).
PIP_INDEX = os.environ.get("PIP_INDEX_URL", "")


def load_tasks(tasks_dir: Path) -> list[Task]:
    tasks: list[Task] = []
    for jl in sorted(tasks_dir.glob("*.jsonl")):
        tasks.extend(parse_swebench_jsonl(jl))
    return tasks


def build_model(model_id: str):
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise SystemExit("DEEPSEEK_API_KEY is not set in .env; cannot run a real model.")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    # DeepSeek V4 models are reasoning models: keep thinking ON (coding needs
    # it) and raise the token budget so the chain-of-thought isn't truncated
    # before the first tool call. Do NOT force tool_choice — the loop terminates
    # on "no tool calls".
    is_v4 = "v4" in model_id
    return OpenAIModel(
        model=model_id,
        base_url=base_url,
        api_key=api_key,
        max_tokens=8192,
        # DeepSeek V4 thinking mode is incompatible with tool_calls (400s on
        # multi-turn tool use); disable it like the CUA harness does.
        extra_body={"thinking": {"type": "disabled"}} if is_v4 else None,
    )


async def run_one(
    task: Task,
    model,
    repos_dir: Path,
    output_dir: Path,
    image: str,
    step_limit: int,
) -> RunResult:
    repo_path = repos_dir / task.id
    task.repo_path = str(repo_path)
    if not repo_path.exists():
        return RunResult(
            task_id=task.id, exit_status="missing-checkout", error=f"no checkout at {repo_path}"
        )

    try:
        runtime = DockerRuntime(image=image, mount_path=repo_path)
    except DockerError as exc:
        return RunResult(task_id=task.id, exit_status="sandbox-error", error=str(exc))

    try:
        # Safety net: ensure pytest is present (no-op when the image already has it).
        pip_index = f"-i {PIP_INDEX} " if PIP_INDEX else ""
        setup = runtime.run_command_sync(
            f"python -m pip install --quiet --disable-pip-version-check {pip_index}pytest",
            timeout=300,
        )
        if setup["returncode"] != 0:
            return RunResult(
                task_id=task.id,
                exit_status="setup-error",
                error=f"failed to ensure pytest: {setup['output'][:400]}",
            )
    except Exception as exc:  # noqa: BLE001 - never crash the batch
        return RunResult(task_id=task.id, exit_status="setup-error", error=str(exc))

    runner = Runner(
        model,
        runtime=runtime,
        output_dir=output_dir,
        step_limit=step_limit,
        sandbox="docker",
        docker_image=image,
    )
    return await runner.run(task)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default=str(DEFAULT_TASKS))
    parser.add_argument("--repos", default=str(DEFAULT_REPOS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--step-limit", type=int, default=25)
    args = parser.parse_args()

    if not docker_available():
        print(
            "error: Docker daemon is unavailable; cannot run the Docker sandbox "
            "(run with --sandbox local to use the local runtime instead).",
            file=sys.stderr,
        )
        return 1

    tasks = load_tasks(Path(args.tasks))
    if not tasks:
        print(f"error: no tasks found in {args.tasks}", file=sys.stderr)
        return 1

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    model = build_model(args.model)

    print(f"Running {len(tasks)} SWE-bench task(s) with model={args.model} in Docker...")
    results: list[RunResult] = []
    for task in tasks:
        print(f"\n=== {task.id} ===")
        result = await run_one(
            task, model, Path(args.repos), output_dir, args.image, args.step_limit
        )
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
