"""Repo spec: a payment system with a cross-module ledger bug."""

REPO = "payment"

FILES = {
    "payment/__init__.py": "",
    "payment/gateway.py": '''"""Gateway: charge a card and return the transaction id."""


def charge(amount: float) -> str:
    return "txn_123"


def fee(amount: float) -> float:
    return amount * 0.03
''',
    "payment/ledger.py": '''"""Ledger: record transactions."""


class Ledger:
    def __init__(self):
        self._entries = []

    def record(self, txn_id: str, amount: float):
        self._entries.append((txn_id, amount))

    def total(self) -> float:
        return sum(a for _, a in self._entries)
''',
    "payment/payment.py": '''"""Payment: the public charge API."""

from payment.gateway import charge, fee
from payment.ledger import Ledger


class PaymentService:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def charge(self, amount: float) -> str:
        txn_id = charge(amount)
        self.ledger.record(txn_id, amount)
        return txn_id
''',
}

TESTS = {
    "tests/test_payment.py": '''"""Tests for payment (ledger amount bug surfaces via total)."""

from payment.ledger import Ledger
from payment.payment import PaymentService


def test_charge_returns_txn_id():
    svc = PaymentService(Ledger())
    assert svc.charge(100.0) == "txn_123"


def test_ledger_records_amount():
    ledger = Ledger()
    svc = PaymentService(ledger)
    svc.charge(100.0)
    assert ledger.total() == 100.0


def test_ledger_records_multiple():
    ledger = Ledger()
    svc = PaymentService(ledger)
    svc.charge(50.0)
    svc.charge(30.0)
    assert ledger.total() == 80.0
''',
}

TASKS = [
    {
        "id": "payment-ledger-amount",
        "instruction": (
            "Fix the bug where the payment ledger records the wrong amount for "
            "each transaction. The test 'test_ledger_records_amount' fails "
            "because the ledger total doesn't match the charged amount. Find "
            "the root cause."
        ),
        "difficulty": "hard",
        "category": "cross-module",
        "lines": 1,
        "bug": [
            ("payment/payment.py",
             "        self.ledger.record(txn_id, amount)\n",
             "        self.ledger.record(txn_id, fee(amount))\n"),
        ],
        "fail_to_pass": [
            "tests/test_payment.py::test_ledger_records_amount",
        ],
        "pass_to_pass": [
            "tests/test_payment.py::test_charge_returns_txn_id",
        ],
    },
]
