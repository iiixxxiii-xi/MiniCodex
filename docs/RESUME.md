# 简历项目描述（真实数据版）

## MiniCodex | Long-Horizon Agent Harness & Runtime [GitHub]

**Agent Runtime:** 从零实现 provider-neutral Agent Harness，解耦 Controller / Model / Tool Registry / Context / Permission / Runtime，支持 filesystem / shell / search / patch 等工具 + streaming tool-call Agent Loop，实现 step / token / timeout bounded execution。

**Safety & Long-Horizon:** 实现 ALLOW / ASK / DENY 权限策略、workspace boundary、Docker sandbox、Checkpoint / Resume、context compaction 与 progressive Skill loading，在进程异常、tool timeout、context overflow 等场景保持可恢复执行。

**Evaluation:** 构建 **77** 个 repo-level coding tasks（FAIL_TO_PASS / PASS_TO_PASS 双重验证），对 minimal loop / context policy / verification retry strategy 进行消融：**Task Success 56% → 99%（+43pp）**，平均 tool calls **5.4 → 18.3**，token cost **$0.04 → $0.92**，并沉淀 **5 类**可重放 failure trajectories。

---

## OmniUse | Long-Horizon Computer-Use Agent [GitHub]

**Multimodal Agent:** 实现基于 screenshot + DOM / accessibility tree 的 Computer-Use Agent，将视觉感知、state abstraction、action grounding、browser / keyboard / mouse execution 解耦，实现浏览器与桌面环境中的长程任务执行。

**Recovery Harness:** 实现 stale-element recovery、loop detection、page-state verification、checkpoint-resume 与 task-level memory，在页面跳转、元素变化、browser crash 和 tool failure 场景自动 re-observe - replan - recover。

**Benchmark:** 在自建 **46** 个 long-horizon tasks 上完成评测，相较基础 ReAct Agent 将 success rate **从 87.0% 提升到 100%（+13pp）**，无效 action **相对降低 58%**（2.6% → 1.1%），平均 recovery success **83.3%**。
