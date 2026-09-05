"""Ledger: record transactions."""


class Ledger:
    def __init__(self):
        self._entries = []

    def record(self, txn_id: str, amount: float):
        self._entries.append((txn_id, amount))

    def total(self) -> float:
        return sum(a for _, a in self._entries)
