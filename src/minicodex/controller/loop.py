from __future__ import annotations

import json
import logging
import time

from minicodex.controller.budgets import BudgetTracker
from minicodex.controller.exceptions import FormatError, LimitsExceeded
from minicodex.controller.policies.context import ContextPolicy
from minicodex.controller.policies.retry import RequeryPolicy
from minicodex.core.events import (
    ActionEvent,
    ErrorEvent,
    Event,
    EventSink,
    EventSource,
    InvalidToolCallEvent,
    ModelCallEvent,
    ObservationEvent,
    StepEvent,
)
from minicodex.core.messages import make_message
from minicodex.core.types import StepOutput
from minicodex.model.base import ModelError, ModelResponse, ToolCall, Usage
from minicodex.model.schema import drop_invalid_tool_calls
from minicodex.toolsource.base import DuplicateToolError, ToolSource
from minicodex.toolsource.builtin import BuiltinToolSource

logger = logging.getLogger(__name__)


class AgentLoop:
    """Thin main loop. Query the model, resolve tool calls, execute them against
    the env, repeat — driven by exceptions (LimitsExceeded / FormatError /
    ModelError).
    """

    def __init__(
        self,
        model,
        env,
        *,
        step_limit: int = 0,
        token_limit: int = 0,
        cost_limit: float = 0.0,
        max_requeries: int = 3,
        tools: list[dict] | None = None,
        tool_sources: list[ToolSource] | None = None,
        event_sink: EventSink | None = None,
        model_name: str = "",
        stream: bool = False,
        context_policy: str = "none",
        context_window: int = 20,
        truncation_limit: int = 8000,
        offload_dir: str | None = None,
        retry_policy: str = "fixed",
    ):
        self.model = model
        self.env = env
        self.budgets = BudgetTracker(step_limit=step_limit, token_limit=token_limit, cost_limit=cost_limit)
        self.requery = RequeryPolicy(max_requeries=max_requeries, policy=retry_policy)
        self.context_policy = ContextPolicy(
            name=context_policy,
            window=context_window,
            max_len=truncation_limit,
            offload_dir=offload_dir,
        )
        self.tools = tools or []
        self._sources = self._build_sources(tool_sources)
        self._schemas, self._source_by_name = self._index_sources(self._sources)
        self.messages: list[dict] = []
        self.event_sink = event_sink
        self.model_name = model_name
        self.stream = stream

    def _emit(self, event: Event) -> None:
        """Forward ``event`` to the sink, if one is attached."""
        if self.event_sink is not None:
            self.event_sink.append(event)

    async def run(self, task: str = "") -> StepOutput:
        self.messages = [make_message("system", "You are a coding agent."), make_message("user", task)]
        try:
            while True:
                try:
                    output = await self.step()
                    self.requery.reset()
                    if output.done:
                        logger.info("agent finished normally after %d steps", self.budgets.steps)
                        return StepOutput(done=True, exit_status="finished")
                except FormatError as exc:
                    exit_status = "RepeatedFormatError"
                    recoverable = self.requery.should_requery()
                    self._emit(
                        ErrorEvent(
                            source=EventSource.CONTROLLER,
                            error_type="FormatError",
                            recoverable=recoverable,
                            message=str(exc),
                        )
                    )
                    if not recoverable:
                        logger.error("%s after %d consecutive errors", exit_status, self.requery.n_requeries)
                        return StepOutput(done=True, exit_status=exit_status)
                    logger.warning("requery after format error: %s", exc)
                    self.messages.append(make_message("user", f"Invalid response: {exc}"))
                except ModelError as exc:
                    exit_status = "ModelError"
                    recoverable = self.requery.should_requery()
                    self._emit(
                        ErrorEvent(
                            source=EventSource.CONTROLLER,
                            error_type="ModelError",
                            recoverable=recoverable,
                            message=str(exc),
                        )
                    )
                    if not recoverable:
                        logger.error("model error not recoverable: %s", exc)
                        return StepOutput(done=True, exit_status=exit_status)
                    logger.warning("requery after model error: %s", exc)
                    self.messages.append(make_message("user", f"Model error: {exc}"))
                except LimitsExceeded as exc:
                    logger.info("limits exceeded: %s", exc.reason)
                    return StepOutput(done=True, exit_status="LimitsExceeded")
                except Exception as exc:  # defensive last resort: never let the loop crash
                    self._emit(
                        ErrorEvent(
                            source=EventSource.CONTROLLER,
                            error_type=type(exc).__name__,
                            recoverable=False,
                            message=str(exc),
                        )
                    )
                    logger.exception("unexpected error in agent loop: %s", exc)
                    return StepOutput(done=True, exit_status="Error")
        finally:
            self._cleanup()

    async def step(self) -> StepOutput:
        self.budgets.check()
        start = time.monotonic()
        model_start = time.monotonic()
        if self.stream:
            response = await self._collect_stream(self.model.stream(self.messages, self._schemas))
            # Streaming adapters emit raw argument fragments, so schema
            # validation of the merged tool calls happens here in the loop.
            response = drop_invalid_tool_calls(response, self._schemas)
        else:
            response = await self.model.query(self.messages, self._schemas)
        model_latency_ms = (time.monotonic() - model_start) * 1000
        self.budgets.register_step()
        self.budgets.add_tokens(response.usage.input_tokens, response.usage.output_tokens)
        self.budgets.add_cost(response.usage.cost_usd)
        self._emit(
            ModelCallEvent(
                source=EventSource.MODEL,
                model=self.model_name,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cost_usd=response.usage.cost_usd,
                latency_ms=model_latency_ms,
            )
        )
        tool_calls = [{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in response.tool_calls]
        self.messages.append(
            make_message(
                "assistant",
                response.thought,
                tool_calls=tool_calls,
                reasoning_content=response.reasoning_content,
            )
        )
        for tool_call in response.tool_calls:
            try:
                action = self._resolve(tool_call)
            except FormatError as exc:
                self._emit(
                    InvalidToolCallEvent(
                        source=EventSource.CONTROLLER,
                        tool_name=tool_call.name,
                        reason=str(exc),
                    )
                )
                raise
            action_event = ActionEvent(
                source=EventSource.AGENT,
                tool_name=tool_call.name,
                tool_call_id=tool_call.id,
                action=action,
            )
            self._emit(action_event)
            source = self._source_for(tool_call.name)
            tool_start = time.monotonic()
            observation = await source.call(action["name"], action["arguments"])
            self._emit(
                ObservationEvent(
                    source=EventSource.RUNTIME,
                    tool_name=tool_call.name,
                    tool_call_id=tool_call.id,
                    action_id=action_event.id,
                    observation=observation,
                    latency_ms=(time.monotonic() - tool_start) * 1000,
                )
            )
            observation_text = self.context_policy.process_observation(repr(observation))
            self.messages.append(
                make_message("tool", observation_text, tool_name=tool_call.name, tool_call_id=tool_call.id)
            )
        self.messages = self.context_policy.process_messages(self.messages)
        self._emit(
            StepEvent(
                source=EventSource.CONTROLLER,
                step_index=self.budgets.steps - 1,
                duration_ms=(time.monotonic() - start) * 1000,
            )
        )
        return StepOutput(done=not response.tool_calls)

    async def _collect_stream(self, stream) -> ModelResponse:
        """Merge incremental stream chunks into one final :class:`ModelResponse`.

        ``thought`` accumulates across chunks (streaming text deltas). Tool calls
        arrive in one of two ways:

        * complete ``tool_calls`` on a single chunk (adapters that buffer the
          full message, e.g. the mock), or
        * incremental ``tool_call_deltas`` whose ``arguments`` JSON fragments are
          concatenated per ``index`` and parsed once the stream ends.

        ``usage`` and ``stop_reason`` are taken from the last chunk that carries
        them.
        """
        thought_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        usage = Usage()
        stop_reason = ""
        delta_slots: dict[int, dict] = {}
        async for chunk in stream:
            if chunk.thought:
                thought_parts.append(chunk.thought)
            for delta in chunk.tool_call_deltas:
                slot = delta_slots.setdefault(delta.index, {"id": "", "name": "", "fragments": []})
                if delta.id:
                    slot["id"] = delta.id
                if delta.name:
                    slot["name"] = delta.name
                if delta.arguments:
                    slot["fragments"].append(delta.arguments)
            if chunk.tool_calls:
                tool_calls = list(chunk.tool_calls)
            if chunk.usage and (chunk.usage.input_tokens or chunk.usage.output_tokens):
                usage = chunk.usage
            if chunk.stop_reason:
                stop_reason = chunk.stop_reason
        if delta_slots:
            tool_calls = self._parse_tool_call_deltas(delta_slots)
        return ModelResponse(
            thought="".join(thought_parts),
            tool_calls=tool_calls,
            usage=usage,
            stop_reason=stop_reason,
        )

    @staticmethod
    def _parse_tool_call_deltas(delta_slots: dict[int, dict]) -> list[ToolCall]:
        """Build complete :class:`ToolCall` objects from accumulated fragments.

        Fragment order within a tool call is preserved by concatenation; argument
        JSON that fails to parse degrades to an empty dict rather than raising,
        so a malformed stream never crashes the loop.
        """
        tool_calls: list[ToolCall] = []
        for index in sorted(delta_slots):
            slot = delta_slots[index]
            raw = "".join(slot["fragments"])
            try:
                arguments = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                arguments = {}
            if not isinstance(arguments, dict):
                arguments = {}
            tool_calls.append(ToolCall(id=slot["id"], name=slot["name"], arguments=arguments))
        return tool_calls

    def _resolve(self, tool_call) -> dict:
        if not tool_call.name:
            raise FormatError(f"Tool call '{tool_call.id}' has no resolvable tool name.")
        return {"name": tool_call.name, "arguments": tool_call.arguments}

    def _build_sources(self, tool_sources: list[ToolSource] | None) -> list[ToolSource]:
        """Return the pluggable tool sources for this loop.

        When ``tool_sources`` is omitted the loop keeps its legacy behaviour by
        exposing a single :class:`BuiltinToolSource` wrapping ``env`` and the
        (possibly policy-filtered) ``tools`` schema list.
        """
        if tool_sources is not None:
            return list(tool_sources)
        return [BuiltinToolSource(self.env, schemas=self.tools)]

    def _index_sources(self, sources: list[ToolSource]) -> tuple[list[dict], dict[str, ToolSource]]:
        """Merge every source's schemas and map each tool name to its source."""
        schemas: list[dict] = []
        by_name: dict[str, ToolSource] = {}
        for source in sources:
            for schema in source.schemas():
                schemas.append(schema)
                name = schema.get("function", {}).get("name")
                if not name:
                    continue
                if name in by_name:
                    raise DuplicateToolError(f"tool '{name}' is provided by more than one source")
                by_name[name] = source
        return schemas, by_name

    def _source_for(self, name: str) -> ToolSource:
        """Resolve a tool name to its owning source, falling back to built-in."""
        source = self._source_by_name.get(name)
        if source is not None:
            return source
        for candidate in self._sources:
            if isinstance(candidate, BuiltinToolSource):
                return candidate
        return self._sources[0]

    def _cleanup(self) -> None:
        stop = getattr(self.env, "stop", None)
        if callable(stop):
            stop()
        for source in self._sources:
            close = getattr(source, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:  # noqa: BLE001 - best-effort teardown
                    logger.warning("failed to close tool source %r", source, exc_info=True)
