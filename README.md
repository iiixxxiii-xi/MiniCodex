# MiniCodex

从零实现的 **Coding Agent Harness** —— 自己控制 `Model → Context → Agent Loop → Tool → Sandbox → Verification` 的完整 Runtime，不是 LangChain 套壳。

**研究问题：为什么现代 Coding Agent 的 Harness 越来越薄？模型能力增长后，哪些 Runtime primitive 仍然不可替代？**

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

**Agent Runtime** — provider-neutral Model Adapter、native tool calling、streaming、retry / timeout / cancellation、max step / max token / max cost 三重预算。

**Tool Runtime** — `read_file` · `write_file` · `grep/search` · `apply_patch` · `shell` · `git diff` · `git status` · `test_runner`。

**安全** — ALLOW / ASK / DENY 权限策略、shell 命令风险分级、workspace boundary、Docker 沙箱（bind-mount + conda env）、secret masking。

**Context** — sliding window、observation truncation、context compaction（摘要-落盘）、progressive Skill loading。

**Long-Horizon** — checkpoint / resume、state persistence、crash recovery、append-only event log（唯一事实源）。

## 消融实验（核心贡献）

在 SWE-bench 子集上比较四类 Harness，回答「哪些 primitive 不可替代」：

| Harness | Task Success | Avg Tool Calls | Token Cost | Latency |
|---------|-------------|----------------|-----------|---------|
| Minimal | 18/22 (81.8%) | 54.1 | $2.18 | 6.3 min |
| + Context Policy | 19/22 (86.4%) | 56.8 | $2.19 | 7.4 min |
| + Verification | 20/22 (90.9%) | 59.1 | $2.53 | 11.4 min |
| 复杂（全开） | 20/22 (90.9%) | 55.6 | $2.07 | 11.2 min |

**结论：** verification 是唯一有方向性收益的 primitive；context / retry 在强模型下无增量，complex ≈ verification。→ 支撑「Harness 变薄」的判断（Recovery / Invalid 两指标在此 regime 无信号，均为 1.0 / 0.0）。

## 快速开始

```bash
uv sync
uv run minicodex run tasks/smoke.json --mock   # 无 API key、无成本跑通

# SWE-bench 基准
uv run python scripts/build_swebench50_prebuilt.py   # 构建实例
uv run python scripts/run_swebench50_ablation.py     # 四臂消融
```

## 参考

[mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent)（极简 Harness）· [OpenHands](https://github.com/All-Hands-AI/OpenHands)（SDK / CLI / sandbox）· DeepAgents（sub-agent / checkpoint）
