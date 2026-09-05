"""Pricing: compute line totals with discounts."""


def discount_rate(customer_tier: str) -> float:
    rates = {"regular": 0.0, "silver": 0.05, "gold": 0.10, "vip": 0.15}
    return rates.get(customer_tier, 0.0)


def line_total(unit_price: float, qty: int, customer_tier: str) -> float:
    rate = discount_rate(customer_tier)
    return unit_price * qty * (1 - rate / 2)
