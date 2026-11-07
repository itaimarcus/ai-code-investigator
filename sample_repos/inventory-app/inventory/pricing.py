from inventory.products import Product

BULK_DISCOUNT_THRESHOLD = 20
BULK_DISCOUNT_RATE = 0.10


def calculate_total(product: Product, quantity: int) -> float:
    total = product.unit_price * quantity
    if quantity > BULK_DISCOUNT_THRESHOLD:
        total *= 1 - BULK_DISCOUNT_RATE
    return round(total, 2)
