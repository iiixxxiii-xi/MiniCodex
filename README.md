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

MiniCodex 是一个从零写起的 coding agent 运行时。不依赖「LangChain → Tools → Prompt → GPT API」的拼装，而是自己控制 `Model → Context → Agent Loop → Tool → Sandbox → Verification` 的完整链路——每一块都能拆开、替换、消融。

**为什么做它：** SWE-agent 在 2024 年给 agent 堆了一堆工具和特殊接口；一年后模型变强了，其中很多东西根本不需要。MiniCodex 想量化这件事——把 Harness 拆到底，再一块块加回去，看哪些 primitive 在强模型下仍然不可替代。

## 核心能力

- **Agent Runtime** — provider-neutral Model Adapter、native tool calling、streaming、retry / timeout / cancellation、max step / max token / max cost 三重预算
- **Tool Runtime** — `read_file` · `write_file` · `grep` · `apply_patch` · `shell` · `git diff` · `git status` · `test_runner`
- **安全** — ALLOW / ASK / DENY 权限策略、shell 命令风险分级、workspace boundary、Docker 沙箱、secret masking
- **Context** — sliding window、observation truncation、context compaction（摘要-落盘）、progressive Skill loading
- **Long-Horizon** — checkpoint / resume、state persistence、crash recovery、append-only event log（唯一事实源）

## 消融实验（回答研究问题）

在 SWE-bench 子集上比较四类 Harness：

| Harness | Task Success | Avg Tool Calls | Token Cost | Latency |
|---------|-------------|----------------|-----------|---------|
| Minimal | 18/22 (81.8%) | 54.1 | $2.18 | 6.3 min |
| + Context Policy | 19/22 (86.4%) | 56.8 | $2.19 | 7.4 min |
| + Verification | 20/22 (90.9%) | 59.1 | $2.53 | 11.4 min |
| 复杂（全开） | 20/22 (90.9%) | 55.6 | $2.07 | 11.2 min |

**结论：** verification 是唯一有方向性收益的 primitive；context / retry 在强模型下无增量，complex ≈ verification——支撑「Harness 变薄」的判断。

## 快速开始

```bash
uv sync
uv run minicodex run tasks/smoke.json --mock   # 无 API key、无成本跑通

# SWE-bench 基准
uv run python scripts/build_swebench50_prebuilt.py   # 构建实例
uv run python scripts/run_swebench50_ablation.py     # 四臂消融
```

## 参考

- [mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent) — 极简 Harness（100 行 agent）
- [OpenHands](https://github.com/All-Hands-AI/OpenHands) — SDK / CLI / sandbox 架构
- [DeepAgents](https://github.com/langchain-ai/deepagents) — sub-agent / checkpoint / filesystem
