# MiniCodex 设计文档

- 日期：2026-08-31
- 状态：已确认，待实现
- 定位：Long-Horizon Agent Harness & Runtime（研究型工程，非玩具）
- 项目根：`D:\minicodex`

## 1. 项目定位与「新」在哪

MiniCodex 是一个**从零实现**的 provider-neutral coding-agent harness，附带一套 evaluation 闭环。

它不是「仿 Claude Code」，而是研究一个命题：

> **为什么现代 Coding Agent 的 Harness 越来越薄？哪些 Runtime primitive 在模型能力增长后仍然不可替代？**

这个命题落进代码的方式是一条架构原则：**主循环（Controller）压到极薄；稳定性、可评估性、安全做成可插拔的旁路（sidecar），不写死进主循环。** 这样既能对照「薄 harness vs 全功能 harness」的差异，也能系统地对各旁路做消融（ablation）。

参考并综合了四个项目：
- **mini-swe-agent**：三抽象薄 loop（Agent/Model/Environment 全协议化）、异常驱动控制流、dict 消息、`role="exit"` 终止信号。
- **SWE-agent 完整版**：requery 错误恢复、autosubmit 抢救、history processor、六类 budget 上限，作为「可选旁路」而非主循环硬编码。
- **DeepAgents**：文件系统 = 统一 Backend 抽象、非破坏式 context compaction、增量 checkpoint、grader rubric、progressive skill loading、sub-agent 状态隔离。
- **OpenHands**：事件日志作为唯一真相源（`BaseEvent{id,timestamp,source}` + `kind` 判别 + Action/Observation 用 `action_id`/`tool_call_id` 双向链接）、工具四维 annotations、确认策略与安全分析器解耦。

## 2. 架构总览：六个可解耦组件

```
                        ┌─────────────────────────────┐
                        │         Controller          │  ← agent loop 控制流
                        │   (step/token/timeout 有界)   │
                        └──────┬──────────────┬───────┘
                               │ 问模型        │ 调工具
                    ┌──────────▼───┐      ┌───▼─────────────┐
                    │    Model     │      │  Tool Registry  │
                    │ (provider-   │      │ filesystem/shell│
                    │  neutral)    │      │  search/patch   │
                    └──────────┬───┘      └───┬─────────────┘
                               │              │ 执行前过 Permission
                    ┌──────────▼──────────────▼─────────────┐
                    │             Context                   │  ← sliding/truncation/compaction
                    └──────────┬────────────────────────────┘
                               │
                    ┌──────────▼────────────────────────────┐
                    │           Permission                  │  ← ALLOW/ASK/DENY + boundary
                    └──────────┬────────────────────────────┘
                               │
                    ┌──────────▼────────────────────────────┐
                    │            Runtime                    │  ← Docker/bubblewrap sandbox
                    └───────────────────────────────────────┘
                               │
                    ┌──────────▼────────────────────────────┐
                    │         Event Log (append-only)       │  ← 唯一真相源
                    └───────────────────────────────────────┘
```

六个组件全部通过「事件日志」解耦，互不直接调用，靠 `action_id` / `tool_call_id` 关联。这条日志同时是 checkpoint、指标提取、崩溃恢复、失败轨迹回放的唯一来源。

## 3. 组件详细设计

### 3.1 Controller（Agent Loop）

核心循环保持极薄（对标 mini-swe-agent 的 `while True: self.step()`）：

```
history → model.query → (thought, tool_calls) → runtime.execute → observations → history
```

- 终止是**数据**不是控制流：任何想结束的方往消息流里塞一条 `role="exit"`，附 `exit_status` / `submission`。
- 异常驱动控制流：`FormatError` / `LimitsExceeded` / `TimeExceeded` / `Submitted` 等异常携带 message，主循环 catch 后决定重试或退出。
- **有界执行（bounded execution）**：三类预算在 `query` 前检查——`step_limit`（步数）、`token_limit`（token）、`cost_limit`（USD），外加 `wall_time_limit`，任一触顶即终止。
- **旁路（可插拔，非写死）**：
  - `verification retry strategy`：格式错/工具被拦时，用错误模板回灌模型重问（requery），上限 `max_requeries`；硬错误触发 autosubmit 抢救（从环境抠出 patch 提交）。
  - `context policy`：见 3.4。
  - `tool policy`：工具集的选择与组合。

### 3.2 Model（Provider-neutral Adapter）

自写薄协议，不用 litellm 重依赖：

```python
class Model(Protocol):
    def query(self, messages, tools) -> ModelResponse: ...   # 含 thought + tool_calls
    def stream(self, messages, tools) -> Iterator[...]: ...  # streaming
    def cancel(self): ...                                    # cancellation
```

- 两个实现：`AnthropicModel` / `OpenAIModel`，各自处理 native tool calling、streaming、retry/timeout（指数退避，区分「可重试」与「重试无意义」错误）、token/cost 统计。
- token 统计用官方 usage 字段；cost 按模型价目表折算。

### 3.3 Tool Registry

每个工具 = 声明式定义，单一定义驱动「LLM 的 function-calling schema」和「安全层判定」：

```python
Tool(name, description, parameters: JSONSchema, annotations: {read_only, destructive, idempotent})
```

工具分组（对应简历）：

| 分组 | 工具 | 说明 |
|---|---|---|
| filesystem | read_file / write_file | 带行号、带截断 |
| shell | shell | 沙箱内执行 bash |
| search | grep / glob | 代码库检索 |
| patch | apply_patch | 底层调 `git apply` |
| git | git_diff / git_status | 工作区状态 |
| verify | test_runner | 跑测试取回通过/失败（eval 核心） |

`git` 与 `verify` 是 eval 闭环的支撑工具；简历 headline 的四类 = filesystem/shell/search/patch。

### 3.4 Context

- **sliding context**：上下文超限时只保留最近 N 轮，旧的滑出。
- **observation truncation**：工具返回超长则截断，并显式告知模型「输出被截断，换更小命令」。
- **context compaction**（非破坏式，抄 DeepAgents）：超阈值时把旧消息压成摘要 + 原文 offload 到文件（`/conversation_history/{id}.md`），摘要带 `source=compaction` 标签注入；raw 历史保留，供回放与评估。
- **artifact/file reference**：大文件或工具产物不塞进对话，用「引用路径」指代，模型需要时再读。
- **progressive Skill loading**：按需加载技能提示词（SKILL.md），而非一开始全量注入。

### 3.5 Permission（安全）

- **ALLOW / ASK / DENY** 三态策略，可配置。
- **shell command risk classification**：命令风险分级（`ls` 低危、`rm -rf` 高危），依据工具 annotations + 命令模式。
- **workspace boundary**：命令只能作用于任务目录内。
- **secret masking**：日志中 API key / 密码打码。

### 3.6 Runtime（Sandbox）

- **Docker**（主用，Windows 走 WSL2）：`docker run -d ... sleep` + `docker exec ... bash -lc <cmd>`，带 timeout / interrupt。
- **bubblewrap**（Linux-only）：`unshare` 命名空间隔离，作为 Docker 之外的轻量方案，与 Docker 形成「重/轻」两档 sandbox 对照。
- **local**（快速开发用，无隔离，仅测试）。

## 4. Event Log 与 Long-Horizon

- **Event Log**：JSONL append-only。事件基类 `{id, timestamp, source, kind}`，`source ∈ {controller, model, tool, permission, runtime, user}`。
- **checkpoint / resume**：每一步把状态（消息流 + 已执行动作 + 计数器）落盘为 checkpoint；恢复 = 从最近 checkpoint 重放。
- **state persistence**：状态落盘，不依赖内存。
- **crash recovery**：进程崩溃后从最近 checkpoint 恢复，事件日志保证可重放。
- **replayable failure trajectories**：失败轨迹（含错误中间态）完整记录，可回放，作为评估与研究素材。
- **sub-agent**（借鉴 DeepAgents）：`task` 工具 spawn 子 agent，状态白名单隔离（不传父对话历史、排除私有字段），结果折叠成单条结构化回传。

三类恢复场景（简历）——进程异常、tool timeout、context overflow——均由「event log + checkpoint + 非破坏 compaction」覆盖。

## 5. Evaluation 设计

### 5.1 指标（全部从 Event Log 精确提取）

| 指标 | 定义 |
|---|---|
| Task Success | 通过 hidden test 的 task / 总数 |
| 平均 Tool Calls | 总 tool_call 次数 / task 数（成功/失败分开报） |
| Token Cost | 总 input/output token + USD 成本 |
| Latency | 每 task wall-clock 时间 + 每 step 平均 |
| Recovery Rate | 遇到可恢复错误后仍产出合法 submission 的占比 |
| Invalid Tool Call Rate | 非法调用（参数错/未知工具/被拦）/ 总调用 |

### 5.2 Task 集与基准

- **自造 task 集**：50~80 个 repo-level coding tasks，每个带明确的 PASS/FAIL 测试。
- **SWE-bench 子集**：跑 SWE-bench Verified 30~50 个真实 issue。

### 5.3 Ablation 设计

对同一批 task，一键切换以下维度，产出对比表：

- **minimal loop** vs **full harness**（薄 vs 全旁路）
- **context policy**：sliding-only / +compaction / +truncation
- **tool policy**：工具集不同组合（含/不含 test_runner、含/不含 patch 等）
- **verification retry strategy**：无 retry / 固定 retry / 退避 retry

## 6. 技术栈

- Python 3.12（用 `uv` 建隔离环境，避开系统 3.14 的 wheel 兼容问题）
- pydantic v2（配置与事件 schema）
- typer（CLI）
- jinja2（prompt 模板）
- anthropic / openai 官方 SDK（Model 层）
- docker（Runtime 层）
- pytest（测试）

## 7. 目录结构

```
minicodex/
├── src/minicodex/
│   ├── core/            # Event / Message / 配置 schema（唯一真相源）
│   ├── controller/      # Agent Loop + 预算 + 旁路 policy
│   ├── model/           # provider-neutral Model 协议 + anthropic/openai
│   ├── registry/        # Tool Registry（工具声明 + schema 生成）
│   ├── runtime/         # 工具实现 + sandbox（docker/local/bubblewrap）
│   ├── context/         # sliding / truncation / compaction / file-reference / skills
│   ├── permission/      # ALLOW/ASK/DENY + 风险分级 + boundary + masking
│   ├── state/           # event log + checkpoint/resume + sub-agent
│   ├── eval/            # metrics + task runner + swebench + ablation + report
│   └── cli/
├── tasks/               # 自造 task 集
├── tests/
└── docs/plans/
```

## 8. 范围（统一，一个项目）

MiniCodex 是一个**完整、统一的项目**，原始需求中的所有功能一次性纳入范围，不做版本切分、不删功能：

- Agent Runtime（provider-neutral adapter、native tool calling、streaming、retry/timeout、cancellation、三类 budget）
- Tool Runtime（filesystem / shell / search / patch / git / verify）
- 安全（ALLOW/ASK/DENY、风险分级、workspace boundary、Docker/bubblewrap sandbox、secret masking）
- Context（sliding、truncation、compaction、artifact/file reference、progressive skill loading）
- Long-Horizon（checkpoint/resume、state persistence、crash recovery、event log、sub-agent）
- Evaluation（自造 task 集、SWE-bench 子集、六指标、三类 policy 消融、replayable failure trajectories）

实现会按依赖顺序推进（先 core/controller/model 打地基，再 runtime/permission/context，最后 state/eval 收口）——这是**工程顺序**，不是版本切分，最终交付的是一个完整闭环的项目。
