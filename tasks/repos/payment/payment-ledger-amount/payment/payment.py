"""Payment: the public charge API."""

from payment.gateway import charge, fee
from payment.ledger import Ledger


class PaymentService:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def charge(self, amount: float) -> str:
        txn_id = charge(amount)
        self.ledger.record(txn_id, fee(amount))
        return txn_id
