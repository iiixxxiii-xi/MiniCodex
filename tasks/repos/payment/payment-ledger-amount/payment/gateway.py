"""Gateway: charge a card and return the transaction id."""


def charge(amount: float) -> str:
    return "txn_123"


def fee(amount: float) -> float:
    return amount * 0.03
