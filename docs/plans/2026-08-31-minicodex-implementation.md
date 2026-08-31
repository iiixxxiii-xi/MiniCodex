# MiniCodex Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 从零实现一个 provider-neutral、可评估、可恢复的 Long-Horizon coding-agent harness（含 Docker sandbox、安全层、事件日志、六指标 eval 闭环），并在自造 task 集 + SWE-bench 子集上跑出消融报告。

**Architecture:** 六个解耦组件（Controller / Model / Tool Registry / Context / Permission / Runtime）+ append-only Event Log 作为唯一真相源。主循环极薄，稳定性与评估做成可插拔旁路。参考 mini-swe-agent（薄 loop + 异常驱动）、SWE-agent（requery/autosubmit 旁路）、DeepAgents（非破坏 compaction、checkpoint）、OpenHands（事件日志 + action_id/tool_call_id 关联）。

**Tech Stack:** Python 3.12（uv 管理）、pydantic v2、typer、jinja2、anthropic/openai SDK、pytest、subprocess 调 docker CLI。

**执行顺序：** 按依赖推进（core → model → controller → registry/runtime → sandbox → permission → context → state → eval → cli）。每 phase 内部严格 TDD：先写失败测试 → 跑红 → 实现 → 跑绿 → 提交。

---

## Phase 0：环境与脚手架

**Files:**
- Create: `pyproject.toml`、`.gitignore`、`.python-version`、`src/minicodex/__init__.py`、`tests/conftest.py`、`tests/test_smoke.py`

**Step 1：配置 uv 项目与依赖**

在 `D:\minicodex` 下执行（uv 已装，缓存与 Python 已指向 D 盘）：

```bash
cd /d/minicodex
uv python install 3.12
uv init --no-workspace --python 3.12
```

**Step 2：写 `pyproject.toml`**（覆盖 uv init 生成的）：

```toml
[project]
name = "minicodex"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.7",
    "typer>=0.12",
    "jinja2>=3.1",
    "anthropic>=0.40",
    "openai>=1.50",
]

[dependency-groups]
dev = ["pytest>=8.0", "pytest-asyncio>=0.24"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 3：写 `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.trajs/
results/
*.log
```

**Step 4：同步依赖 + 写 smoke test**

```bash
uv sync
```

`tests/test_smoke.py`：

```python
import minicodex


def test_importable():
    assert minicodex.__version__ is not None
```

`src/minicodex/__init__.py`：

```python
__version__ = "0.1.0"
```

**Step 5：跑测试并提交**

```bash
uv run pytest -v
git add -A && git commit -m "chore: project scaffolding with uv + pytest"
```

---

## Phase 1：core（事件、消息、配置类型）

**目标：** 定义整个项目共享的类型骨架——`Event`、`Message`、`ToolCall`、`StepOutput`、`Config`。这是「唯一真相源」。

**Files:**
- Create: `src/minicodex/core/__init__.py`、`src/minicodex/core/events.py`、`src/minicodex/core/messages.py`、`src/minicodex/core/types.py`、`src/minicodex/core/config.py`
- Test: `tests/core/test_events.py`、`tests/core/test_messages.py`

### Task 1.1：Event 基类与判别联合

**Step 1：写失败测试** `tests/core/test_events.py`

```python
from minicodex.core.events import Event, ActionEvent, ObservationEvent, EventSource


def test_event_base_fields():
    e = Event(source=EventSource.MODEL, kind="action")
    assert e.id
    assert e.timestamp
    assert e.source == EventSource.MODEL


def test_action_observation_link():
    a = ActionEvent(source=EventSource.AGENT, tool_name="shell", tool_call_id="c1", action={"command": "ls"})
    o = ObservationEvent(source=EventSource.RUNTIME, tool_name="shell", tool_call_id="c1",
                          action_id=a.id, observation={"output": "x"})
    assert o.action_id == a.id
    assert o.tool_call_id == "c1"
```

**Step 2：跑红** `uv run pytest tests/core/test_events.py -v` → FAIL（模块不存在）

**Step 3：实现** `src/minicodex/core/events.py`

```python
from __future__ import annotations
import time, uuid
from enum import Enum
from pydantic import BaseModel, Field


class EventSource(str, Enum):
    CONTROLLER = "controller"
    MODEL = "model"
    TOOL = "tool"
    PERMISSION = "permission"
    RUNTIME = "runtime"
    USER = "user"


class Event(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = Field(default_factory=time.time)
    source: EventSource
    kind: str


class ActionEvent(Event):
    kind: str = "action"
    tool_name: str
    tool_call_id: str
    action: dict


class ObservationEvent(Event):
    kind: str = "observation"
    tool_name: str
    tool_call_id: str
    action_id: str
    observation: dict
```

**Step 4：跑绿，Step 5：提交。**

### Task 1.2：Message 与 StepOutput

`src/minicodex/core/messages.py`（消息就是普通 dict，role + content + extra）：

```python
def make_message(role: str, content: str, **extra) -> dict:
    return {"role": role, "content": content, "extra": extra}
```

`src/minicodex/core/types.py`（StepOutput + exit 约定）：

```python
from dataclasses import dataclass, field


@dataclass
class StepOutput:
    thought: str = ""
    action: dict | None = None
    observation: dict | None = None
    done: bool = False
    exit_status: str = ""
    submission: str = ""
```

`src/minicodex/core/config.py`（pydantic 配置根，供各组件继承）：

```python
from pydantic import BaseModel


class AgentConfig(BaseModel):
    step_limit: int = 50
    token_limit: int = 200_000
    cost_limit: float = 5.0
    wall_time_limit_seconds: int = 0
```

测试覆盖：`make_message` 的 extra 合并、`StepOutput` 默认 done=False、`AgentConfig` 默认值。

---

## Phase 2：Model（provider-neutral 适配器）

**目标：** 自写薄 `Model` 协议 + `MockModel`（测试用，零 API key）+ `AnthropicModel`/`OpenAIModel`（native tool calling + streaming + retry/timeout + token/cost 统计）。

**Files:**
- Create: `src/minicodex/model/__init__.py`、`src/minicodex/model/base.py`、`src/minicodex/model/mock.py`、`src/minicodex/model/anthropic.py`、`src/minicodex/model/openai.py`、`src/minicodex/model/usage.py`
- Test: `tests/model/test_mock.py`、`tests/model/test_usage.py`

### Task 2.1：Model 协议 + ModelResponse

`src/minicodex/model/base.py`：

```python
from __future__ import annotations
from typing import Any, Iterator, Protocol
from pydantic import BaseModel


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class ModelResponse(BaseModel):
    thought: str = ""
    tool_calls: list[ToolCall] = []
    usage: Usage = Usage()
    stop_reason: str = ""


class Model(Protocol):
    def query(self, messages: list[dict], tools: list[dict]) -> ModelResponse: ...
    def stream(self, messages: list[dict], tools: list[dict]) -> Iterator[ModelResponse]: ...
    def cancel(self) -> None: ...
```

### Task 2.2：MockModel（先写测试）

`tests/model/test_mock.py`：

```python
from minicodex.model.mock import MockModel


def test_mock_returns_scripted_response():
    m = MockModel(script=[{"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "ls"}}]}])
    r = m.query([], [])
    assert r.tool_calls[0].name == "shell"
    assert r.tool_calls[0].arguments == {"command": "ls"}


def test_mock_increments_usage():
    m = MockModel()
    m.query([], [])
    assert m.total_input_tokens > 0
```

实现 `MockModel`：按脚本序列返回预设 response，`usage` 每次累加固定 token。

### Task 2.3：Anthropic / OpenAI 实现（真 SDK，留 env 注入）

`src/minicodex/model/anthropic.py`：`AnthropicModel(Model)`，用 `client.messages.create(tools=..., stream=...)`，把原生 tool_use block 转成 `ToolCall`，从 `message.usage` 取 token，按价目表算 cost。retry 用指数退避（区分 429/5xx 可重试 vs 4xx 不重试），`cancel()` 中断进行中的请求。

`src/minicodex/model/openai.py`：`OpenAIModel(Model)`，`client.chat.completions.create`，把 function_call 转成 `ToolCall`，同样 retry/timeout/cancel。

> 这两个类不做 mock 测试（涉及真实 API），用单元测试覆盖「把 SDK 返回结构转成 ModelResponse」的纯函数，真实调用留到 Phase 10 集成冒烟。

---

## Phase 3：Controller（Agent Loop）

**目标：** 极薄主循环 + 三类预算 + 可插拔旁路。这是「从零实现 harness」的心脏，也是「为什么 harness 薄」的证据。

**Files:**
- Create: `src/minicodex/controller/__init__.py`、`src/minicodex/controller/loop.py`、`src/minicodex/controller/budgets.py`、`src/minicodex/controller/policies/__init__.py`、`src/minicodex/controller/policies/retry.py`
- Test: `tests/controller/test_loop.py`、`tests/controller/test_budgets.py`

### Task 3.1：Budgets（先写测试）

`tests/controller/test_budgets.py`：

```python
from minicodex.controller.budgets import BudgetTracker


def test_step_limit_exceeded():
    b = BudgetTracker(step_limit=3, token_limit=999, cost_limit=999)
    for _ in range(3):
        b.register_step()
    assert b.exceeded
    assert b.reason == "step_limit"


def test_cost_limit():
    b = BudgetTracker(step_limit=99, token_limit=999, cost_limit=1.0)
    b.add_cost(1.5)
    assert b.exceeded
    assert b.reason == "cost_limit"
```

实现 `budgets.py`：`BudgetTracker` 累计 step/token/cost，`exceeded` + `reason` 属性。

### Task 3.2：薄主循环（先写测试）

`tests/controller/test_loop.py`（用 MockModel + 假 env）：

```python
from minicodex.controller.loop import AgentLoop
from minicodex.model.mock import MockModel


class FakeEnv:
    def execute(self, action):
        return {"output": "ok", "returncode": 0}


def test_loop_runs_until_exit():
    model = MockModel(script=[
        {"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "ls"}}]},
        {"tool_calls": []},  # 触发 exit
    ])
    loop = AgentLoop(model=model, env=FakeEnv())
    result = loop.run(task="do thing")
    assert result.exit_status == "finished"


def test_loop_hits_step_limit():
    model = MockModel(script=[{"tool_calls": [{"id": "1", "name": "shell", "arguments": {"command": "ls"}}]}])
    loop = AgentLoop(model=model, env=FakeEnv(), step_limit=2)
    result = loop.run(task="x")
    assert result.exit_status == "LimitsExceeded"
```

实现 `loop.py`（对标 mini-swe-agent 的 `while True: self.step()`，异常驱动）：

```python
def step(self) -> StepOutput:
    self.budgets.check()          # 触顶抛 LimitsExceeded
    response = self.model.query(self.messages, self.tools)
    self.messages.append(...)
    for tc in response.tool_calls:
        action = self.registry.resolve(tc)          # 解析工具
        if action is None:
            raise FormatError(...)                  # 未知工具 → retry 旁路
        observation = self.env.execute(action)
        self.messages.append(observation_message(observation))
    return StepOutput(done=self._should_stop(response))
```

### Task 3.3：retry 旁路（verification retry strategy）

`policies/retry.py`：把 `FormatError` / 未知工具 / 空 tool_call 的错误回灌模型重问，上限 `max_requeries`。测试：连续格式错达到上限后 `exit_status=RepeatedFormatError`。

---

## Phase 4：Tool Registry + Runtime 工具 + local runtime（走通骨架）

**目标：** 声明式工具 → function-calling schema 自动生成；实现 filesystem/shell/search/patch 工具 + local runtime。此 phase 结束时，**用 MockModel 能把一个 agent 跑通**（不联网、不用 Docker）。

**Files:**
- Create: `src/minicodex/registry/__init__.py`、`src/minicodex/registry/schema.py`、`src/minicodex/registry/registry.py`；`src/minicodex/runtime/__init__.py`、`src/minicodex/runtime/base.py`、`src/minicodex/runtime/local.py`、`src/minicodex/runtime/tools/{read_file,write_file,grep,apply_patch,shell,git,test_runner}.py`
- Test: `tests/registry/test_schema.py`、`tests/runtime/test_local.py`

### Task 4.1：Tool 声明 → schema（先写测试）

`tests/registry/test_schema.py`：

```python
from minicodex.registry.schema import Tool, to_function_schema


def test_tool_to_openai_schema():
    t = Tool(name="read_file", description="Read a file",
             parameters={"type": "object", "properties": {"path": {"type": "string"}},
                         "required": ["path"]},
             annotations={"read_only": True})
    s = to_function_schema(t)
    assert s["type"] == "function"
    assert s["function"]["name"] == "read_file"
    assert s["function"]["parameters"]["required"] == ["path"]
```

实现 `schema.py`：`Tool` pydantic 模型（name/description/parameters/annotations）+ `to_function_schema`。

### Task 4.2：ToolRegistry

`registry.py`：`register(Tool)`、`resolve(name) -> Tool`、`schemas() -> list[dict]`（全量 function schema 给模型）、`annotations_for(name)`。测试：注册/解析/重名报错。

### Task 4.3：Runtime 协议 + local runtime

`runtime/base.py`：`Runtime(Protocol)`，`execute(action: dict) -> dict`、`start()/stop()`。

`runtime/local.py`：`LocalRuntime`，用 `subprocess.run` 执行 shell 命令（`shell` 工具走这里），文件操作直接走 `pathlib`。**local runtime 无隔离，只用于测试和快速开发。**

`runtime/tools/read_file.py`：读文件，返回带行号文本，超长截断。`write_file.py`：写文件。`grep.py`：用 `subprocess` 调 `grep -rn` 或纯 Python 匹配（Windows 兼容用纯 Python）。`apply_patch.py`：`git apply`。`git.py`：`git diff`/`git status`。`test_runner.py`：`pytest` 或项目测试命令。

> 每个工具配一个 TDD 测试（如 read_file 截断、grep 命中、apply_patch 成功/失败）。这是 Phase 4 的主体，逐工具推进、逐工具提交。

---

## Phase 5：Runtime Sandbox（Docker）

**目标：** `DockerRuntime`，对标 mini-swe-agent 的 `docker run -d sleep` + `docker exec bash -lc`，带 timeout/interrupt；`bubblewrap` 只留接口。

**Files:**
- Create: `src/minicodex/runtime/sandbox/__init__.py`、`src/minicodex/runtime/sandbox/docker.py`、`src/minicodex/runtime/sandbox/bubblewrap.py`
- Test: `tests/runtime/sandbox/test_docker.py`

**关键点：**
- `_start_container()`：`docker run -d --name <uuid> -w /workspace <image> sleep 2h`，返回 container_id。
- `execute(command, timeout=30)`：`docker exec -w /workspace <id> bash -lc <cmd>`，`subprocess.run(timeout=...)`，超时中断。
- `cleanup()`：`docker rm -f <id>`。
- 测试：**标记 `@pytest.mark.docker`**（需要 Docker Desktop 运行才跑；否则 skip）。覆盖：启动容器 → 执行 `echo hi` → 断言输出 → 清理。

> **前置提醒（写进 README）：** Docker Desktop 需重启后运行，且要在设置里把「Disk image location」指到 D 盘（省 C 盘空间）。

---

## Phase 6：Permission（安全层）

**目标：** ALLOW/ASK/DENY 三态 + shell 命令风险分级 + workspace boundary + secret masking。

**Files:**
- Create: `src/minicodex/permission/__init__.py`、`src/minicodex/permission/policy.py`、`src/minicodex/permission/risk.py`、`src/minicodex/permission/boundary.py`、`src/minicodex/permission/masking.py`
- Test: `tests/permission/test_policy.py`、`tests/permission/test_risk.py`、`tests/permission/test_masking.py`

**关键点（TDD 逐项）：**
- `policy.py`：`PermissionPolicy`，`decide(tool, action) -> ALLOW|ASK|DENY`，规则按 tool annotations + 命令匹配。测试：read_only 工具 ALLOW、`rm -rf` DENY、未知命令 ASK。
- `risk.py`：`classify(command) -> LOW|MEDIUM|HIGH`，用模式匹配（`rm -rf`/`curl | sh`/`sudo` → HIGH；`ls`/`cat`/`git status` → LOW）。测试各档。
- `boundary.py`：`is_within_workspace(path, root)`，`..`/绝对路径逃逸检测。测试：`../etc` 拒绝、`./sub/file` 放行。
- `masking.py`：`mask(text, secrets)`，把 API key/密码替换成 `***`。测试：`sk-abc123` → `sk-***`。

---

## Phase 7：Context（sliding / truncation / compaction / file-reference / skills）

**目标：** 上下文管理五种策略，全部作为可插拔 processor。

**Files:**
- Create: `src/minicodex/context/__init__.py`、`src/minicodex/context/sliding.py`、`src/minicodex/context/truncation.py`、`src/minicodex/context/compaction.py`、`src/minicodex/context/file_reference.py`、`src/minicodex/context/skills.py`
- Test: `tests/context/test_sliding.py`、`tests/context/test_truncation.py`

**关键点（TDD 逐项）：**
- `sliding.py`：`slide(messages, n)` 只保留最近 n 条，前面的滑出（system message 永远保留）。
- `truncation.py`：`truncate_observation(text, max_len)` 超长截断，并附加「输出被截断」提示。测试截断边界 + 提示注入。
- `compaction.py`：非破坏式——旧消息压缩成 summary + 原文 offload 到文件，raw 保留。测试：压缩后 messages 变短但 raw 仍完整。
- `file_reference.py`：大内容替换成路径引用。`skills.py`：按需加载 SKILL.md。

---

## Phase 8：State（Event Log + Checkpoint/Resume + sub-agent）

**目标：** append-only 事件日志 + 增量 checkpoint + 崩溃恢复 + sub-agent（状态隔离）。

**Files:**
- Create: `src/minicodex/state/__init__.py`、`src/minicodex/state/event_log.py`、`src/minicodex/state/checkpoint.py`、`src/minicodex/state/subagent.py`
- Test: `tests/state/test_event_log.py`、`tests/state/test_checkpoint.py`

**关键点（TDD 逐项）：**
- `event_log.py`：`EventLog.append(event)` 写 JSONL；`replay()` 读回全量事件。测试：写入→读回一致、可重放。
- `checkpoint.py`：每步把（messages + 计数器 + 已执行动作）序列化落盘；`load()` 恢复。测试：保存→加载后状态一致；模拟崩溃后从最近 checkpoint 恢复。
- `subagent.py`：`task` 工具 spawn 子 agent，状态白名单隔离（不传父 messages、排除私有字段），结果折叠成单条 ToolMessage。测试：子 agent 看不到父历史、结果结构化回传。

---

## Phase 9：Eval（指标 + task runner + SWE-bench + ablation + report）

**目标：** 六指标精确提取 + 自造 task 集 + SWE-bench 子集 + 消融 + 报告。这是「闭环」的收口。

**Files:**
- Create: `src/minicodex/eval/__init__.py`、`src/minicodex/eval/metrics.py`、`src/minicodex/eval/task.py`、`src/minicodex/eval/runner.py`、`src/minicodex/eval/swebench.py`、`src/minicodex/eval/ablation.py`、`src/minicodex/eval/report.py`；`tasks/` 下自造 task 集
- Test: `tests/eval/test_metrics.py`

**关键点（TDD 逐项）：**
- `metrics.py`：从 event log 算六指标。测试：给一段已知轨迹，断言 Task Success / tool calls / token cost / latency / recovery rate / invalid rate 数值正确。
- `task.py`：`Task` 定义（repo、issue、gold patch、测试命令）。`runner.py`：跑一个 task → 收集轨迹 + 指标 → 判定 PASS/FAIL（跑 hidden test）。
- `swebench.py`：加载 SWE-bench Verified 子集（`datasets` 库或本地 jsonl），转成 `Task`。
- `ablation.py`：一键切换 policy 组合（minimal loop / context / tool / retry），跑同一批 task。
- `report.py`：产出对比表（markdown + csv）。
- **自造 task 集**：造 50~80 个小 repo task，每个带明确 PASS/FAIL 测试。

---

## Phase 10：CLI + 端到端集成

**目标：** 命令行入口 + 一次真实 run 跑通（真模型 + Docker）。

**Files:**
- Create: `src/minicodex/cli/__init__.py`、`src/minicodex/cli/main.py`、`src/minicodex/__main__.py`、`README.md`
- Test: `tests/test_cli.py`（CLI 参数解析 + --help）

**CLI 命令（typer）：**

```bash
minicodex run --config config.yaml --model anthropic/claude-sonnet-5 --task <task-path>
minicodex eval --tasks tasks/ --model ... --policies minimal,full
minicodex report --results results/
```

**端到端冒烟**：真 Anthropic 模型 + Docker runtime 跑一个 hello-world task，确认产出 patch + 轨迹 + 指标（此步需要 API key，作为可选手动验证，写进 README）。

---

## 完成标准（全部闭环可验证）

1. `uv run pytest` 全绿。
2. MockModel + local runtime 能跑通一个 task（不联网）。
3. Docker runtime 跑通一个 task（`pytest -m docker`）。
4. 六指标从事件日志正确算出（有单测断言数值）。
5. 自造 task 集上跑出消融对比表（markdown + csv）。
6. `minicodex run/eval/report` 三个命令可用。
