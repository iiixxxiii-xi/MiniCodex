"""Inventory: track stock levels and reserve/release items."""


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
