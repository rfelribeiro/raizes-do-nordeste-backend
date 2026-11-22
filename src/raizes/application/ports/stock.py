"""Porta de persistência do estoque."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from raizes.domain.stock.stock import Stock, StockMovement


class StockRepository(Protocol):
    def get_for_update(self, unit_id: UUID, product_ids: list[UUID]) -> dict[UUID, Stock]:
        """Trava as linhas (FOR UPDATE) em ordem de `product_id`, evitando deadlock (RNF-11)."""
        ...

    def save(self, stock: Stock, movements: Sequence[StockMovement]) -> None:
        """Persiste o saldo e acrescenta os movimentos ao razão."""
        ...
