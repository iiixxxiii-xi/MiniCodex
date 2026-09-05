# MiniCodex

一个从零实现、模型无关（provider-neutral）的**编程 Agent 框架（harness）**，内置 **SWE-bench 评测流水线**。它驱动 LLM 在沙箱里解决 repo 级 bug，把每一步写入 append-only 事件日志，并计算六项指标产出消融报告。

核心研究问题：**模型能力增长后，哪些 runtime primitive 仍然不可替代？**——把 harness 消融到裸循环，再逐项加回 primitive 来回答。

## 结果（SWE-bench，22 实例）

四个 harness 预设，跑同一批 22 个实例（deepseek-v4-pro，step 100，thinking 开，并发 8）：

| 预设 | 成功率 | 平均 tool calls | 平均成本 |
|------|--------|----------------|----------|
| `minimal` — 裸 ReAct 循环 + 工具 | 18/22 (81.8%) | 54.1 | $2.18 |
| `context` — + 摘要-落盘压缩 | 19/22 (86.4%) | 56.8 | $2.19 |
| `verification` — + `done` 前回归校验 | 20/22 (90.9%) | 59.1 | $2.53 |
| `complex` — context + verification + retry | 20/22 (90.9%) | 55.6 | $2.07 |

**核心结论：** verification 是唯一有方向性收益的 primitive（81.8% → 90.9%，+9pp，22 实例内方差范围内），代价是 +16% 成本、约 2× 延迟。context 压缩与 retry 在 verification 之上无增量，且都不降低 token 成本——与 2026 年「thin harness」结论一致（强模型下工具/harness 面基本不影响成功率）。

## 架构

六个解耦组件，通过 append-only 事件日志（唯一事实源）连接，指标、检查点、轨迹都从它重放：

- **Controller** — 薄 ReAct 循环，step / token / timeout 三重有界执行。
- **Model** — 模型适配层（OpenAI 兼容；DeepSeek v4 thinking 模式）。
- **Tool Registry** — 声明式工具（filesystem、shell、patch、`test_runner` …）。
- **Context** — 窗口策略 + token 触发的「摘要-落盘」压缩。
- **Permission** — allow / ask / deny 策略 + workspace 边界。
- **Runtime** — local + Docker 沙箱（bind-mount、conda 环境、代理注入）。

## 安装

Python 3.12+ 与 [`uv`](https://docs.astral.sh/uv/)：

```bash
uv sync
```

## 运行

用 **MockModel 可全链路无 key、无成本**跑通：

```bash
uv run minicodex run   tasks/smoke.json --mock
uv run minicodex eval  tasks/ --mock --output-dir results/
uv run minicodex report results/
```

### SWE-bench 基准

从官方预构建镜像（`swebench/sweb.eval.x86_64.<owner>_1776_<repo>-<issue>`）构建 22 实例子集，再跑四臂消融：

```bash
uv run python scripts/build_swebench50_prebuilt.py   # 拉镜像、抽取 /testbed、双向校验
uv run python scripts/run_swebench50_ablation.py     # 4 臂，step 100，并发 8
```

真实模型运行需在 `.env` 里配置 `DEEPSEEK_API_KEY`。结果写到 `results/swebench50-ablation/<arm>/`，汇总到 `summary.json`。

### 消融臂

| 臂 | context | verification | retry |
|----|---------|--------------|-------|
| `minimal` | — | — | — |
| `context` | 摘要-落盘 | — | — |
| `verification` | — | `done` 前回归校验 | — |
| `complex` | ✓ | ✓ | 固定 requery |

每臂固定模型、任务、镜像、step 预算，只变 harness primitive。

## 任务格式

任务是一个 JSON（或 `.jsonl` 每行一条）：

```json
{
  "id": "write-file",
  "repo": "write-file",
  "instruction": "在 workspace 根目录创建 answer.txt。",
  "gold_patch": "create answer.txt",
  "test_command": "python -c \"import os,sys; sys.exit(0 if os.path.exists('answer.txt') else 1)\""
}
```

用 `test_command` 检查最终 workspace，退出码 0 即 PASS；`gold_patch` 是参考补丁（不自动应用）。SWE-bench 实例则携带 `FAIL_TO_PASS` / `PASS_TO_PASS` 测试列表 + gold `patch`，按双向标准打分（所有 F2P 通过 且 所有 P2P 仍通过）。

## 六项指标

每次运行后从事件日志计算：

| 指标 | 定义 |
|------|------|
| **Task Success** | `submission.passed`（隐藏测试退出码） |
| **Avg Tool Calls** | `action` ÷ `step` 事件数 |
| **Token Cost** | `model_call.cost_usd` 之和 |
| **Latency** | `step.duration_ms` 之和 |
| **Recovery Rate** | 可恢复 error 中继续执行的比例 |
| **Invalid Tool Call Rate** | `invalid_tool_call` 占比 |

## 测试

```bash
uv run pytest -v
```

## 目录结构

```
src/minicodex/          核心实现
  controller/           ReAct 循环（step/token/timeout 有界）
  runtime/              local + Docker 沙箱、内建工具
  context/              上下文策略与「摘要-落盘」压缩
  model/                模型适配层
  eval/                 runner、六指标、消融
scripts/                基准构建/运行脚本（早期废弃尝试归档在 scripts/legacy/）
tasks/                  任务定义（SWE-bench 在 tasks/swebench50/，自建任务在 tasks/*.json）
tests/                  单元测试
```
