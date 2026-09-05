"""Tests for payment (ledger amount bug surfaces via total)."""

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
