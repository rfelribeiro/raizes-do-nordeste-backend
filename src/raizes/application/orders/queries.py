"""RF-08: listar e consultar pedidos, com escopo por perfil (RF-03, RNF-03)."""

from uuid import UUID

from raizes.application.errors import PermissionDeniedError
from raizes.application.ports.orders import OrderFilter, OrderRepository
from raizes.application.principal import Principal
from raizes.domain.orders.order import Order
from raizes.domain.shared.enums import OrderChannel, OrderStatus, Role
from raizes.domain.shared.errors import NotFoundError

_STAFF = (Role.ATENDENTE, Role.COZINHA, Role.GERENTE)


class ListOrders:
    def __init__(self, orders: OrderRepository) -> None:
        self._orders = orders

    def execute(
        self,
        principal: Principal,
        *,
        channel: OrderChannel | None,
        status: OrderStatus | None,
        unit_id: UUID | None,
        page: int,
        limit: int,
    ) -> tuple[list[Order], int]:
        customer_id: UUID | None = None
        if principal.role is Role.CLIENTE:
            customer_id = principal.user_id  # só os próprios pedidos
        elif principal.role in _STAFF:
            if principal.unit_id is None or (unit_id is not None and unit_id != principal.unit_id):
                raise PermissionDeniedError("Você só pode consultar pedidos da sua unidade.")
            unit_id = principal.unit_id
        elif principal.role is not Role.ADMIN:
            raise PermissionDeniedError("Você não tem permissão para esta operação.")
        return self._orders.list(
            OrderFilter(channel=channel, status=status, unit_id=unit_id, customer_id=customer_id),
            page,
            limit,
        )


class GetOrder:
    def __init__(self, orders: OrderRepository) -> None:
        self._orders = orders

    def execute(self, principal: Principal, order_id: UUID) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise _not_found()
        if principal.role is Role.CLIENTE:
            if order.customer_id != principal.user_id:
                raise _not_found()  # não revela a existência do pedido de outro cliente
        elif principal.role in _STAFF:
            if not principal.is_staff_of(order.unit_id):
                raise PermissionDeniedError("Este pedido pertence a outra unidade.")
        elif principal.role is not Role.ADMIN:
            raise PermissionDeniedError("Você não tem permissão para esta operação.")
        return order


def _not_found() -> NotFoundError:
    return NotFoundError("Pedido não encontrado.")
