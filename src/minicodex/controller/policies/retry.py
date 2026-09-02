from __future__ import annotations

import time

RETRY_POLICIES = ("none", "fixed", "backoff")


class RequeryPolicy:
    """Requery policy: decides whether (and how) to feed an error back to the
    model for another query.

    ``policy`` selects the strategy:

    - ``none``    — never requery (a single error ends the run).
    - ``fixed``   — requery up to ``max_requeries`` consecutive times, no delay.
    - ``backoff`` — same budget, but sleep with exponential backoff between
      requeries (``base_delay * 2 ** (attempt - 1)``, capped at ``max_delay``).

    ``max_requeries <= 0`` means "no requery" regardless of policy. ``sleep`` is
    injectable so backoff is testable without real wall-clock delays.
    """

    def __init__(
        self,
        max_requeries: int = 3,
        *,
        policy: str = "fixed",
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        sleep=time.sleep,
    ):
        if policy not in RETRY_POLICIES:
            raise ValueError(f"unknown retry policy '{policy}'; expected one of {RETRY_POLICIES}")
        self.policy = policy
        self.max_requeries = max_requeries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._sleep = sleep
        self.n_requeries = 0

    def should_requery(self) -> bool:
        if self.policy == "none" or self.max_requeries <= 0:
            return False
        if self.n_requeries >= self.max_requeries:
            return False
        self.n_requeries += 1
        if self.policy == "backoff":
            delay = min(self.base_delay * (2 ** (self.n_requeries - 1)), self.max_delay)
            self._sleep(delay)
        return True

    def reset(self) -> None:
        self.n_requeries = 0
