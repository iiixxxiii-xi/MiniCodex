# MiniCodex

A from-scratch, provider-neutral **coding-agent harness** with a built-in
evaluation loop. It drives an LLM against a sandboxed workspace to solve a
task, records every step to an append-only event log (the single source of
truth), and computes six metrics that feed an ablation report.

**Architecture (one sentence):** six decoupled components — *Controller*
(thin agent loop), *Model* (provider adapters), *Tool Registry* (declarative
tools), *Context* (window/compaction), *Permission* (allow/ask/deny), and
*Runtime* (local + Docker sandbox) — connected by an append-only event log from
which metrics, checkpoints, and trajectories are all replayed.

## Install

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/):

```bash
cd /d/minicodex
uv sync
```

## Run

Everything works end-to-end with a **MockModel — no API key, no cost**:

```bash
# Run one task (PASS/FAIL + metrics)
uv run minicodex run tasks/smoke.json --mock

# Run a task set under every ablation preset and write a report
uv run minicodex eval tasks/ --mock --output-dir results/

# Re-render the comparison table from persisted results
uv run minicodex report results/
```

The `eval` command produces `results/<preset>.json` (raw metrics), plus
`report.md` / `report.csv` comparison tables across policy presets.

### Real-model scoring

Use a real provider by selecting its adapter; credentials come from the
standard environment variables (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`):

```bash
uv run minicodex eval tasks/ --model anthropic/claude-sonnet-5 --output-dir results/
uv run minicodex run  tasks/sum.json  --model openai/gpt-4o
```

For a Docker-sandboxed run, start Docker Desktop first (point its disk-image
location at `D:` to save space), then run the sandbox tests:

```bash
uv run pytest -m docker
```

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
PASS. `gold_patch` is the reference patch (not applied automatically).

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
