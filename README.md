<div align="center">
  <h1>MiniCodex</h1>
  <h3>从零实现的 Coding Agent Harness —— 自己控制 Runtime，不套壳</h3>
  <p><b>研究问题：为什么 Coding Agent 的 Harness 越来越薄？模型能力增长后，哪些 Runtime primitive 仍然不可替代？</b></p>
</div>

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/provider--neutral-000000" alt="provider-neutral">
  <img src="https://img.shields.io/badge/SWE--bench-evaluated-ff69b4" alt="SWE-bench evaluated">
</div>

<br>

## 为什么做它

SWE-agent 在 2024 年给 agent 堆了一堆工具和特殊接口；一年后模型变强了，其中很多东西根本不需要——mini-swe-agent 只用 bash 就打 SWE-bench 76.8%。MiniCodex 想把这个观察做成**可量化的研究**：把 Harness 拆到底，再一块块加回去，看哪些 primitive 在强模型下仍然不可替代。

## Principles

- **从零** — 不套 LangChain；Model / Context / Loop / Tool / Sandbox 每一层自己实现、自己控制
- **provider-neutral** — 任何支持 tool calling 的模型都能接
- **可消融** — 每个 primitive（context / verification / retry）能单独拆掉，回答「哪些不可替代」
- **可观测** — append-only event log 是唯一事实源，轨迹可重放、指标可复算

## 架构

```
             ┌──────── Model ────────┐
             │                       │
User ──→ Context ──→ Agent Loop ──→ Tool Call
                             │
          ┌──────────────────┼──────────────────┐
          ↓                  ↓                  ↓
      Filesystem           Shell           apply_patch
          ↓                  ↓                  ↓
          └────────── Permission / Sandbox ────┘
                             ↓
                       Observation
                             ↓
                   Verification / Test ──→ (loop)
```

## 核心能力

- **Agent Runtime** — provider-neutral Model Adapter、native tool calling、streaming、retry / timeout / cancellation、max step / max token / max cost 三重预算
- **Tool Runtime** — `read_file` · `write_file` · `grep` · `apply_patch` · `shell` · `git diff` · `git status` · `test_runner`（pytest / sympy `bin/test` / django `runtests.py`）
- **安全** — ALLOW / ASK / DENY 权限策略、shell 命令风险分级、workspace boundary、Docker 沙箱（bind-mount + conda env + 代理注入）、secret masking
- **Context** — sliding window、observation truncation、context compaction（摘要-落盘，token 触发）、progressive Skill loading
- **Long-Horizon** — checkpoint / resume、state persistence、crash recovery、append-only event log

## 消融实验

在 SWE-bench 子集（22 实例，官方 pre-built 镜像）上比较四类 Harness：

| Harness | Task Success | Avg Tool Calls | Token Cost | Latency |
|---------|-------------|----------------|-----------|---------|
| Minimal | 18/22 (81.8%) | 54.1 | $2.18 | 6.3 min |
| + Context Policy | 19/22 (86.4%) | 56.8 | $2.19 | 7.4 min |
| + Verification | 20/22 (90.9%) | 59.1 | $2.53 | 11.4 min |
| 复杂（全开） | 20/22 (90.9%) | 55.6 | $2.07 | 11.2 min |

**结论：** verification 是唯一有方向性收益的 primitive（81.8% → 90.9%）；context / retry 在强模型下无增量，complex ≈ verification。

**六项指标**（从 event log 复算）：Task Success、Avg Tool Calls、Token Cost、Latency、Recovery Rate、Invalid Tool Call Rate（后两项在此短任务 regime 无信号：无可恢复错误、无非法工具调用）。

## 安装

```bash
uv sync               # 开发环境（Python 3.12+）
uv tool install .     # 装成全局命令 minicodex（开箱即用，无需 uv run）
```

## 使用方式

### Python API

```python
import asyncio
from minicodex.model.mock import MockModel            # 或 OpenAIModel / AnthropicModel
from minicodex.eval.runner import Runner
from minicodex.eval.task import load_task

task = load_task("examples/smoke.json")
result = asyncio.run(Runner(MockModel(), output_dir="results/").run(task))
print(f"{'PASS' if result.passed else 'FAIL'}  tool_calls={result.metrics.tool_calls}  cost=${result.metrics.cost_usd:.4f}")
```

### CLI（claude 风格）

```bash
minicodex                                    # 直接进对话
> 帮我修一下 D:\myapp\utils.py 的 bug        # 自动定位到 D:\myapp 干活
> :cd D:\另一个项目                            # 换目录
> exit

minicodex 帮我修 D:\myapp\utils.py 的 bug     # 一句话模式（不进入对话）
minicodex run examples/smoke.json --mock      # 单任务 → PASS/FAIL + 指标
```

### 模型

对话默认 `deepseek/v4-pro`（thinking 开）。`--model` 可换：`mock`（无 key）、`anthropic/<id>`、`openai/<id>`、`deepseek/<id>`。

### SWE-bench 基准

```bash
uv run python scripts/build_swebench50_prebuilt.py   # 从官方 pre-built 镜像构建实例
uv run python scripts/run_swebench50_ablation.py     # 四臂消融（step 100，并发 8）
```

真实模型需在 `.env` 配置 `DEEPSEEK_API_KEY`。

## 任务格式

```json
{
  "id": "write-file",
  "repo": "write-file",
  "instruction": "在 workspace 根目录创建 answer.txt。",
  "test_command": "python -c \"import os,sys; sys.exit(0 if os.path.exists('answer.txt') else 1)\""
}
```

SWE-bench 实例携带 `FAIL_TO_PASS` / `PASS_TO_PASS` + gold `patch`，按双向标准打分（所有 F2P 通过 且 所有 P2P 仍通过）。

## 目录结构

```
src/minicodex/       核心实现
  controller/        ReAct 循环
  runtime/           local + Docker 沙箱、内建工具
  context/           上下文策略与压缩
  model/             模型适配层
  eval/              runner、六指标、消融
scripts/             SWE-bench 构建 / 运行脚本
tasks/swebench50/    SWE-bench 基准记录
tests/               单元测试
```

## 参考

- [mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent) — 极简 Harness（100 行 agent）
- [OpenHands](https://github.com/All-Hands-AI/OpenHands) — SDK / CLI / sandbox 架构
- [DeepAgents](https://github.com/langchain-ai/deepagents) — sub-agent / checkpoint / filesystem
