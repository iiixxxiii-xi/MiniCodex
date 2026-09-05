# MiniCodex

A from-scratch, provider-neutral **coding-agent harness** with a built-in
**SWE-bench evaluation pipeline**. It drives an LLM against a sandboxed
workspace to resolve a repo-level bug, records every step to an append-only
event log, and computes six metrics that feed an ablation report.

The research question it was built to answer: **which runtime primitives stay
indispensable as model capability grows?** — answered by ablating the harness
down to a bare loop and adding primitives back one at a time.

## Results (SWE-bench, 22 instances)

Four harness presets, each over the same 22 instances (deepseek-v4-pro,
step limit 100, thinking enabled, concurrency 8):

| Preset | Task Success | Avg tool calls | Avg cost |
|--------|-------------|----------------|----------|
| `minimal` — bare ReAct loop + tools | 18/22 (81.8%) | 54.1 | $2.18 |
| `context` — + summarize-and-offload | 19/22 (86.4%) | 56.8 | $2.19 |
| `verification` — + regression gate on `done` | 20/22 (90.9%) | 59.1 | $2.53 |
| `complex` — context + verification + retry | 20/22 (90.9%) | 55.6 | $2.07 |

**Key finding:** verification is the only primitive with a directional success
gain (81.8% → 90.9%, +9pp, within variance on 22 instances), bought with +16%
spend and ~2× latency. Context compaction and retry add nothing on top of
verification, and none of the primitives reduce token cost on these
short-horizon tasks — consistent with the 2026 "thin harness" result that
tool/harness surface is largely pass-rate-invariant under a strong model.

## Architecture

Six decoupled components connected by an append-only event log (the single
source of truth from which metrics, checkpoints, and trajectories replay):

- **Controller** — thin ReAct agent loop with step / token / timeout bounds.
- **Model** — provider adapters (OpenAI-compatible; DeepSeek v4 thinking mode).
- **Tool Registry** — declarative tools (filesystem, shell, patch, `test_runner`, …).
- **Context** — window policy + token-triggered summarize-and-offload compaction.
- **Permission** — allow / ask / deny policy + workspace boundary.
- **Runtime** — local + Docker sandbox (bind-mount, conda env, proxy injection).

## Install

Python 3.12+ and [`uv`](https://docs.astral.sh/uv/):

```bash
uv sync
```

## Run

Everything works end-to-end with a **MockModel — no API key, no cost**:

```bash
uv run minicodex run   tasks/smoke.json --mock
uv run minicodex eval  tasks/ --mock --output-dir results/
uv run minicodex report results/
```

### SWE-bench benchmark

Build the 22-instance subset from the official pre-built images
(`swebench/sweb.eval.x86_64.<owner>_1776_<repo>-<issue>`), then run the
four-arm ablation:

```bash
uv run python scripts/build_swebench50_prebuilt.py   # pull images, extract /testbed, validate
uv run python scripts/run_swebench50_ablation.py     # 4 arms, step 100, concurrency 8
```

A real run needs `DEEPSEEK_API_KEY` in `.env`. The runner writes per-task
trajectories to `results/swebench50-ablation/<arm>/` and a `summary.json` with
the aggregated six metrics.

### Ablation arms

| Arm | context | verification | retry |
|-----|---------|--------------|-------|
| `minimal` | — | — | — |
| `context` | summarize-and-offload | — | — |
| `verification` | — | regression gate on `done` | — |
| `complex` | ✓ | ✓ | fixed requery |

Every arm holds the model, tasks, images, and step budget fixed; only the
harness primitive differs.

## Task format

A task is a JSON file (or one JSON line per task in a `.jsonl`):

```json
{
  "id": "write-file",
  "repo": "write-file",
  "instruction": "Create a file named answer.txt in the workspace root.",
  "gold_patch": "create answer.txt",
  "test_command": "python -c \"import os,sys; sys.exit(0 if os.path.exists('answer.txt') else 1)\""
}
```

The agent's final workspace is checked with `test_command`; exit code `0` means
PASS. `gold_patch` is the reference patch (not applied automatically). SWE-bench
instances instead carry `FAIL_TO_PASS` / `PASS_TO_PASS` node lists plus a gold
`patch`, and are scored double-directionally (every F2P passes AND every P2P
still passes).

## The six metrics

Computed from the event log after every run:

| Metric | Definition (from events) |
|--------|--------------------------|
| **Task Success** | `submission.passed` (hidden test exit code) |
| **Avg Tool Calls** | `action` events ÷ `step` events |
| **Token Cost** | sum of `model_call.cost_usd` |
| **Latency** | sum of `step.duration_ms` |
| **Recovery Rate** | recoverable `error`s the agent continued after ÷ total recoverable errors |
| **Invalid Tool Call Rate** | `invalid_tool_call` ÷ (`invalid_tool_call` + `action`) |

## Test

```bash
uv run pytest -v
```
