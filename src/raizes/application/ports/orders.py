"""Porta de persistência do agregado Pedido."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from raizes.domain.orders.order import Order
from raizes.domain.shared.enums import OrderChannel, OrderStatus


@dataclass(frozen=True, slots=True)
class OrderFilter:
    """Filtros de listagem; o escopo do perfil (cliente, unidade) entra por aqui."""

    channel: OrderChannel | None = None
    status: OrderStatus | None = None
    unit_id: UUID | None = None
    customer_id: UUID | None = None


class OrderRepository(Protocol):
    def get(self, order_id: UUID) -> Order | None: ...

    def get_for_update(self, order_id: UUID) -> Order | None:
        """Carrega com bloqueio de linha (SELECT ... FOR UPDATE)."""
        ...

    def add(self, order: Order) -> None: ...

    def save(self, order: Order) -> None: ...

    def list(self, filter: OrderFilter, page: int, limit: int) -> tuple[list[Order], int]:
        """Página (1-based) de pedidos e o total que atende ao filtro."""
        ...
