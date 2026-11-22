"""UC-04 Realizar Pedido: pedido, itens, reserva de estoque, histórico, auditoria e outbox numa
só transação (RNF-11)."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from raizes.application.errors import PermissionDeniedError
from raizes.application.ports.audit import AuditEntry, AuditRecorder
from raizes.application.ports.catalog import MenuRepository, UnitRepository
from raizes.application.ports.orders import OrderRepository
from raizes.application.ports.outbox import OutboxWriter
from raizes.application.ports.stock import StockRepository
from raizes.application.ports.unit_of_work import UnitOfWork
from raizes.application.ports.users import UserRepository
from raizes.application.principal import Principal
from raizes.domain.orders.order import Order, OrderItem
from raizes.domain.orders.policies import ChannelPolicy
from raizes.domain.shared.enums import OrderChannel, Role
from raizes.domain.shared.errors import BusinessRuleViolationError, DomainError, NotFoundError
from raizes.domain.stock.stock import Stock, StockMovement


@dataclass(frozen=True, slots=True)
class OrderItemInput:
    product_id: UUID
    quantity: int


@dataclass(frozen=True, slots=True)
class CreateOrderCommand:
    unit_id: UUID
    channel: OrderChannel
    items: list[OrderItemInput]
    customer_id: UUID | None = None


class CreateOrder:
    def __init__(
        self,
        *,
        orders: OrderRepository,
        menu: MenuRepository,
        units: UnitRepository,
        users: UserRepository,
        stock: StockRepository,
        audit: AuditRecorder,
        outbox: OutboxWriter,
        uow: UnitOfWork,
    ) -> None:
        self._orders = orders
        self._menu = menu
        self._units = units
        self._users = users
        self._stock = stock
        self._audit = audit
        self._outbox = outbox
        self._uow = uow

    def execute(self, principal: Principal, command: CreateOrderCommand) -> Order:
        if not ChannelPolicy.can_create_orders(principal.role):
            raise PermissionDeniedError("Seu perfil não pode criar pedidos.")
        ChannelPolicy.validate(principal.role, command.channel)  # 422 (RN-14)
        if principal.role is not Role.CLIENTE and not principal.is_staff_of(command.unit_id):
            raise PermissionDeniedError("Você só pode criar pedidos na sua unidade.")
        if not self._units.exists(command.unit_id):
            raise NotFoundError(
                "Unidade não encontrada.",
                detalhes=[{"field": "unidadeId", "issue": "unidade inexistente ou inativa"}],
            )

        customer_id = self._resolve_customer(principal, command)
        quantities = self._merge_items(command.items)
        items = self._price_items(command.unit_id, quantities)

        order = Order.create(
            unit_id=command.unit_id,
            channel=command.channel,
            creator_id=principal.user_id,
            items=items,
            customer_id=customer_id,
        )
        movements = self._reserve(order, principal)  # 409 aqui: nada foi gravado ainda

        self._orders.add(order)
        for stock, movement in movements:
            self._stock.save(stock, [movement])
        self._audit.record(
            AuditEntry(
                action="PEDIDO_CRIADO",
                resource_type="PEDIDO",
                resource_id=str(order.id),
                user_id=principal.user_id,
                role=principal.role,
                unit_id=order.unit_id,
                channel=order.channel,
                details={
                    "numeroPedido": order.order_number,
                    "qtdItens": len(order.items),
                    "valorTotal": str(order.total_value),
                },
            )
        )
        self._outbox.add(order.pull_events())
        self._uow.commit()
        return order

    def _resolve_customer(self, principal: Principal, command: CreateOrderCommand) -> UUID | None:
        if principal.role is Role.CLIENTE:
            return principal.user_id  # `clienteId` do corpo é ignorado
        if command.customer_id is None:
            return None
        if not self._users.is_active_customer(command.customer_id):
            raise NotFoundError(
                "Cliente não encontrado.",
                detalhes=[{"field": "clienteId", "issue": "cliente inexistente ou inativo"}],
            )
        return command.customer_id

    @staticmethod
    def _merge_items(items: list[OrderItemInput]) -> dict[UUID, int]:
        merged: dict[UUID, int] = {}
        for item in items:
            merged[item.product_id] = merged.get(item.product_id, 0) + item.quantity
        return merged

    def _price_items(self, unit_id: UUID, quantities: dict[UUID, int]) -> list[OrderItem]:
        product_ids = list(quantities)
        offers = self._menu.get_offers(unit_id, product_ids)
        today = datetime.now(UTC).date()
        missing = [pid for pid in product_ids if pid not in offers]
        if missing:
            existing = self._menu.existing_product_ids(missing)
            unknown = [pid for pid in missing if pid not in existing]
            if unknown:
                raise NotFoundError(
                    "Produto não encontrado.",
                    detalhes=[
                        {"field": "itens.produtoId", "issue": f"produto {pid} inexistente"}
                        for pid in unknown
                    ],
                )
            raise DomainError(
                "Produto não ofertado na unidade.",
                codigo="PRODUTO_NAO_OFERTADO",
                detalhes=[
                    {"field": "itens.produtoId", "issue": f"produto {pid} fora do cardápio"}
                    for pid in missing
                ],
            )
        unavailable = [pid for pid in product_ids if not offers[pid].is_orderable(today)]
        if unavailable:
            raise DomainError(
                "Produto indisponível na unidade.",
                codigo="PRODUTO_INDISPONIVEL",
                detalhes=[
                    {"field": "itens.produtoId", "issue": f"produto {pid} indisponível"}
                    for pid in unavailable
                ],
            )
        # RN-10: o preço efetivo do cardápio é congelado no item.
        return [OrderItem(pid, quantities[pid], offers[pid].price) for pid in product_ids]

    def _reserve(self, order: Order, principal: Principal) -> list[tuple[Stock, StockMovement]]:
        """Reserva cada item com as linhas de estoque travadas em ordem de produto (RNF-11)."""
        product_ids = sorted(item.product_id for item in order.items)
        stocks = self._stock.get_for_update(order.unit_id, product_ids)
        problems: list[dict[str, str]] = []
        reserved: list[tuple[Stock, StockMovement]] = []
        for item in sorted(order.items, key=lambda i: i.product_id):
            stock = stocks.get(item.product_id)
            if stock is None:
                problems.append(
                    {"field": "produtoId", "issue": f"produto {item.product_id}: sem estoque"}
                )
                continue
            try:
                movement = stock.reserve(item.quantity, order.id, principal.user_id)
            except BusinessRuleViolationError as error:
                problems.extend(error.detalhes)
                continue
            reserved.append((stock, movement))
        if problems:
            raise BusinessRuleViolationError(
                "Não há quantidade suficiente para um ou mais itens.",
                codigo="ESTOQUE_INSUFICIENTE",
                detalhes=problems,
            )
        return reserved
