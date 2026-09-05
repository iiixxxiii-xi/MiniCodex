"""Orders: place an order, reserving stock and totalling price."""

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
