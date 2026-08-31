from __future__ import annotations


class RequeryPolicy:
    """Requery bypass: counts consecutive format errors and decides whether to
    feed the error back to the model for another query, up to ``max_requeries``.
    """

    def __init__(self, max_requeries: int = 3):
        self.max_requeries = max_requeries
        self.n_requeries = 0

    def should_requery(self) -> bool:
        if self.max_requeries <= 0:
            return True
        if self.n_requeries >= self.max_requeries:
            return False
        self.n_requeries += 1
        return True

    def reset(self) -> None:
        self.n_requeries = 0
