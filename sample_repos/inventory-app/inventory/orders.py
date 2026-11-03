from dataclasses import dataclass

from inventory.pricing import calculate_total
from inventory.products import Product
from inventory.stock import Stock


@dataclass(frozen=True)
class Order:
    product: Product
    quantity: int
    total: float


def place_order(stock: Stock, product: Product, quantity: int) -> Order:
    stock.remove(product.sku, quantity)
    total = calculate_total(product, quantity)
    return Order(product=product, quantity=quantity, total=total)
