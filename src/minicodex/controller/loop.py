from __future__ import annotations

import logging

from minicodex.controller.budgets import BudgetTracker
from minicodex.controller.exceptions import FormatError, LimitsExceeded
from minicodex.controller.policies.retry import RequeryPolicy
from minicodex.core.messages import make_message
from minicodex.core.types import StepOutput
from minicodex.model.base import ModelError

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
    ):
        self.model = model
        self.env = env
        self.budgets = BudgetTracker(step_limit=step_limit, token_limit=token_limit, cost_limit=cost_limit)
        self.requery = RequeryPolicy(max_requeries=max_requeries)
        self.tools = tools or []
        self.messages: list[dict] = []

    def run(self, task: str = "") -> StepOutput:
        self.messages = [make_message("system", "You are a coding agent."), make_message("user", task)]
        try:
            while True:
                try:
                    output = self.step()
                    self.requery.reset()
                    if output.done:
                        logger.info("agent finished normally after %d steps", self.budgets.steps)
                        return StepOutput(done=True, exit_status="finished")
                except FormatError as exc:
                    exit_status = "RepeatedFormatError"
                    if not self.requery.should_requery():
                        logger.error("%s after %d consecutive errors", exit_status, self.requery.n_requeries)
                        return StepOutput(done=True, exit_status=exit_status)
                    logger.warning("requery after format error: %s", exc)
                    self.messages.append(make_message("user", f"Invalid response: {exc}"))
                except ModelError as exc:
                    exit_status = "ModelError"
                    if not self.requery.should_requery():
                        logger.error("model error not recoverable: %s", exc)
                        return StepOutput(done=True, exit_status=exit_status)
                    logger.warning("requery after model error: %s", exc)
                    self.messages.append(make_message("user", f"Model error: {exc}"))
                except LimitsExceeded as exc:
                    logger.info("limits exceeded: %s", exc.reason)
                    return StepOutput(done=True, exit_status="LimitsExceeded")
                except Exception as exc:  # defensive last resort: never let the loop crash
                    logger.exception("unexpected error in agent loop: %s", exc)
                    return StepOutput(done=True, exit_status="Error")
        finally:
            self._cleanup()

    def step(self) -> StepOutput:
        self.budgets.check()
        response = self.model.query(self.messages, self.tools)
        self.budgets.register_step()
        self.budgets.add_tokens(response.usage.input_tokens, response.usage.output_tokens)
        self.budgets.add_cost(response.usage.cost_usd)
        self.messages.append(make_message("assistant", response.thought))
        for tool_call in response.tool_calls:
            action = self._resolve(tool_call)
            observation = self.env.execute(action)
            self.messages.append(
                make_message("tool", repr(observation), tool_name=tool_call.name, tool_call_id=tool_call.id)
            )
        return StepOutput(done=not response.tool_calls)

    def _resolve(self, tool_call) -> dict:
        if not tool_call.name:
            raise FormatError(f"Tool call '{tool_call.id}' has no resolvable tool name.")
        return {"name": tool_call.name, "arguments": tool_call.arguments}

    def _cleanup(self) -> None:
        stop = getattr(self.env, "stop", None)
        if callable(stop):
            stop()
