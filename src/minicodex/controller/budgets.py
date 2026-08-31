from __future__ import annotations

from minicodex.controller.exceptions import LimitsExceeded


class BudgetTracker:
    """Accumulates steps/tokens/cost and reports which limit (if any) is exceeded.

    A limit of ``0`` means "no limit" (matching the mini-swe-agent convention).
    """

    def __init__(self, step_limit: int = 0, token_limit: int = 0, cost_limit: float = 0.0):
        self.step_limit = step_limit
        self.token_limit = token_limit
        self.cost_limit = cost_limit
        self.steps = 0
        self.tokens = 0
        self.cost = 0.0

    def register_step(self) -> None:
        self.steps += 1

    def add_tokens(self, input_tokens: int, output_tokens: int) -> None:
        self.tokens += input_tokens + output_tokens

    def add_cost(self, cost: float) -> None:
        self.cost += cost

    @property
    def reason(self) -> str:
        if self.step_limit > 0 and self.steps >= self.step_limit:
            return "step_limit"
        if self.token_limit > 0 and self.tokens >= self.token_limit:
            return "token_limit"
        if self.cost_limit > 0 and self.cost >= self.cost_limit:
            return "cost_limit"
        return ""

    @property
    def exceeded(self) -> bool:
        return bool(self.reason)

    def check(self) -> None:
        reason = self.reason
        if reason:
            raise LimitsExceeded(reason)
