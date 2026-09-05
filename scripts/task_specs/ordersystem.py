"""Repo spec for a multi-module order system (cross-module bug, hard)."""

REPO = "ordersystem"

FILES = {
    "ordersystem/__init__.py": "",
    "ordersystem/inventory.py": '''"""Inventory: track stock levels and reserve/release items."""


class Inventory:
    def __init__(self):
        self._stock = {}

    def add(self, item_id: str, qty: int) -> None:
        self._stock[item_id] = self._stock.get(item_id, 0) + qty

    def available(self, item_id: str) -> int:
        return self._stock.get(item_id, 0)

    def reserve(self, item_id: str, qty: int) -> bool:
        if self._stock.get(item_id, 0) < qty:
            return False
        self._stock[item_id] -= qty
        return True

    def release(self, item_id: str, qty: int) -> None:
        self._stock[item_id] = self._stock.get(item_id, 0) + qty
''',
    "ordersystem/pricing.py": '''"""Pricing: compute line totals with discounts."""


def discount_rate(customer_tier: str) -> float:
    rates = {"regular": 0.0, "silver": 0.05, "gold": 0.10, "vip": 0.15}
    return rates.get(customer_tier, 0.0)


def line_total(unit_price: float, qty: int, customer_tier: str) -> float:
    rate = discount_rate(customer_tier)
    return unit_price * qty * (1 - rate)
''',
    "ordersystem/orders.py": '''"""Orders: place an order, reserving stock and totalling price."""

from ordersystem.inventory import Inventory
from ordersystem.pricing import line_total


class Order:
    def __init__(self, inventory: Inventory):
        self.inventory = inventory
        self.lines = []

    def add_item(self, item_id: str, unit_price: float, qty: int, tier: str):
        self.lines.append((item_id, unit_price, qty, tier))

    def place(self) -> float:
        total = 0.0
        for item_id, unit_price, qty, tier in self.lines:
            if not self.inventory.reserve(item_id, qty):
                raise ValueError(f"insufficient stock for {item_id}")
            total += line_total(unit_price, qty, tier)
        return total
''',
}

TESTS = {
    "tests/test_orders.py": '''"""Tests for the order system (cross-module: order -> pricing bug)."""

from ordersystem.inventory import Inventory
from ordersystem.orders import Order
from ordersystem.pricing import discount_rate


def test_discount_rate_vip():
    assert discount_rate("vip") == 0.15


def test_order_vip_discount():
    inv = Inventory()
    inv.add("widget", 10)
    order = Order(inv)
    order.add_item("widget", 100.0, 2, "vip")
    # vip is 15% off: 100 * 2 * 0.85 = 170
    assert order.place() == 170.0


def test_order_regular_no_discount():
    inv = Inventory()
    inv.add("widget", 10)
    order = Order(inv)
    order.add_item("widget", 100.0, 2, "regular")
    assert order.place() == 200.0


def test_order_insufficient_stock():
    inv = Inventory()
    inv.add("widget", 1)
    order = Order(inv)
    order.add_item("widget", 100.0, 5, "regular")
    try:
        order.place()
    except ValueError:
        return
    raise AssertionError("expected ValueError for insufficient stock")
''',
}

# One injected cross-module bug: pricing.line_total halves the discount.
TASKS = [
    {
        "id": "ordersystem-vip-discount",
        "instruction": (
            "Fix the bug in the order system where VIP customers get the wrong "
            "discount. The tests fail when placing an order with a VIP customer. "
            "Find the root cause and fix it."
        ),
        "difficulty": "hard",
        "category": "cross-module",
        "lines": 1,
        "bug": [
            ("ordersystem/pricing.py",
             "    return unit_price * qty * (1 - rate)\n",
             "    return unit_price * qty * (1 - rate / 2)\n"),
        ],
        "fail_to_pass": [
            "tests/test_orders.py::test_order_vip_discount",
        ],
        "pass_to_pass": [
            "tests/test_orders.py::test_discount_rate_vip",
            "tests/test_orders.py::test_order_regular_no_discount",
            "tests/test_orders.py::test_order_insufficient_stock",
        ],
    },
]
