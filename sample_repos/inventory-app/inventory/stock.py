class OutOfStockError(Exception):
    """Raised when removing more units than are available."""


class Stock:
    def __init__(self) -> None:
        self._quantities: dict[str, int] = {}

    def available(self, sku: str) -> int:
        return self._quantities.get(sku, 0)

    def add(self, sku: str, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        self._quantities[sku] = self.available(sku) + quantity

    def remove(self, sku: str, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        available = self.available(sku)
        if quantity > available:
            raise OutOfStockError(
                f"Requested {quantity} units of {sku}, but only {available} are available"
            )
        self._quantities[sku] = available - quantity
