"""Ablation over the 21 self-discovered real-repo tasks (Docker sandbox).

Reuses the existing checked-out repos + Docker image, and runs the 4-way
build-up ablation (complex / minimal / minimal+context / minimal+verification)
to see whether `minimal` actually drops (i.e. the tasks are hard enough).
"""
import asyncio
import sys
from pathlib import Path

from minicodex.eval.swebench import parse_swebench_jsonl
from minicodex.eval.ablation import run_ablation, DEFAULT_PRESETS

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_swebench_subset import build_model  # noqa: E402

TASKS_DIR = Path("tasks/swebench")
REPOS_DIR = Path("tasks/swebench/repos")


async def main() -> None:
    tasks = []
    for jl in sorted(TASKS_DIR.glob("*.jsonl")):
        tasks.extend(parse_swebench_jsonl(jl))
    for t in tasks:
        t.repo_path = str(REPOS_DIR / t.id)
    print(f"加载 {len(tasks)} 个任务")

    model = build_model("deepseek-v4-flash")
    presets = [
        DEFAULT_PRESETS["full"],
        DEFAULT_PRESETS["minimal_no_verify"],
        DEFAULT_PRESETS["minimal"],
        DEFAULT_PRESETS["compaction"],
    ]
    results = await run_ablation(
        tasks, model, presets=presets,
        output_dir="results/swebench-ablation",
        concurrency=4, sandbox="docker", docker_image="minicodex-swebench:latest",
    )
    print("\n=== 消融结果 ===")
    for r in results:
        m = r.metrics
        print(f"{r.preset:18s} success={m.success_rate:.3f}  tool_calls={m.avg_tool_calls:.1f}  "
              f"cost=${m.avg_cost_usd:.3f}  latency={m.avg_latency_ms:.0f}ms")


if __name__ == "__main__":
    asyncio.run(main())
