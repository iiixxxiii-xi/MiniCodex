"""Full 4-way ablation over the 31 hard tasks (23 real-repo + 8 cross-module)."""
import asyncio
import sys
from pathlib import Path

from minicodex.eval.swebench import parse_swebench_jsonl
from minicodex.eval.task import load_tasks
from minicodex.eval.ablation import run_ablation, DEFAULT_PRESETS

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_swebench_subset import build_model  # noqa: E402

CROSS = [
    "ordersystem-vip-discount", "cache-lru-eviction", "auth-distinct-tokens",
    "payment-ledger-amount", "pipeline-transform", "scheduler-priority",
    "fs-write-permission", "netclient-retry",
]


async def main() -> None:
    tasks = []
    for jl in sorted(Path("tasks/swebench").glob("*.jsonl")):
        tasks.extend(parse_swebench_jsonl(jl))
    for t in tasks:
        t.repo_path = str(Path("tasks/swebench/repos") / t.id)
    for cid in CROSS:
        tasks.extend(load_tasks(f"tasks/{cid}.json"))
    print(f"加载 {len(tasks)} 个任务")

    model = build_model("deepseek-v4-flash")
    presets = [
        DEFAULT_PRESETS["harness_minimal"],
        DEFAULT_PRESETS["harness_context"],
        DEFAULT_PRESETS["harness_verification"],
        DEFAULT_PRESETS["harness_complex"],
    ]
    results = await run_ablation(
        tasks, model, presets=presets, output_dir="results/full-ablation",
        concurrency=4, sandbox="docker", docker_image="minicodex-swebench:latest",
    )
    print("\n=== 消融结果（6 指标）===")
    for r in results:
        m = r.metrics
        print(
            f"{r.preset:20s} success={m.success_rate:.1%}  tool_calls={m.avg_tool_calls:.1f}  "
            f"cost=${m.avg_cost_usd:.4f}  latency={m.avg_latency_ms:.0f}ms  "
            f"recovery={m.avg_recovery_rate:.2f}  invalid={m.avg_invalid_tool_call_rate:.1%}"
        )


if __name__ == "__main__":
    asyncio.run(main())
