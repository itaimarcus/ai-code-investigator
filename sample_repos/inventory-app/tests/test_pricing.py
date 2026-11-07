from inventory.orders import place_order
from inventory.pricing import calculate_total
from inventory.products import Product
from inventory.stock import Stock

MUG = Product("MUG-01", "Coffee mug", 5.0)


def test_no_discount_below_threshold() -> None:
    assert calculate_total(MUG, 5) == 25.0


def test_bulk_discount_at_threshold() -> None:
    assert calculate_total(MUG, 20) == 90.0


def test_bulk_discount_above_threshold() -> None:
    assert calculate_total(MUG, 30) == 135.0


def test_place_order_applies_bulk_discount_at_threshold() -> None:
    stock = Stock()
    stock.add(MUG.sku, 30)
    order = place_order(stock, MUG, 20)
    assert order.total == 90.0
