"""Tests for the order system (cross-module: order -> pricing bug)."""

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
