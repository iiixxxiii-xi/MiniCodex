"""Re-run the compaction-affected presets (context + complex) plus verification
(to backfill its 1 missing task), keeping the already-valid harness_minimal."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from minicodex.eval.swebench import parse_swebench_jsonl
from minicodex.eval.ablation import run_ablation, DEFAULT_PRESETS
from run_swebench_subset import build_model  # noqa: E402 (loads .env)


async def main() -> None:
    tasks = []
    for jl in sorted(Path("tasks/swebench").glob("*.jsonl")):
        tasks.extend(parse_swebench_jsonl(jl))
    for t in tasks:
        t.repo_path = str(Path("tasks/swebench/repos") / t.id)
    print(f"加载 {len(tasks)} 个自挖任务", flush=True)

    model = build_model("deepseek-v4-flash")
    presets = [
        DEFAULT_PRESETS["harness_context"],
    ]
    results = await run_ablation(
        tasks, model, presets=presets, output_dir="results/swebench-ablation",
        concurrency=4, sandbox="docker", docker_image="minicodex-swebench:latest",
    )
    print("\n=== 消融结果（6 指标）===", flush=True)
    for r in results:
        m = r.metrics
        print(
            f"{r.preset:20s} success={m.success_rate:.1%}  tool_calls={m.avg_tool_calls:.1f}  "
            f"cost=${m.avg_cost_usd:.4f}  latency={m.avg_latency_ms:.0f}ms  "
            f"recovery={m.avg_recovery_rate:.2f}  invalid={m.avg_invalid_tool_call_rate:.1%}",
            flush=True,
        )


if __name__ == "__main__":
    asyncio.run(main())
