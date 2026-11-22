"""UC-06 Atualizar Status do Pedido: perfil e unidade (403) antes da máquina de estados (409)."""

from uuid import UUID

from raizes.application.errors import ApplicationValidationError, PermissionDeniedError
from raizes.application.ports.audit import AuditEntry, AuditRecorder
from raizes.application.ports.orders import OrderRepository
from raizes.application.ports.outbox import OutboxWriter
from raizes.application.ports.unit_of_work import UnitOfWork
from raizes.application.principal import Principal
from raizes.domain.orders.order import Order
from raizes.domain.orders.policies import TransitionPolicy
from raizes.domain.shared.enums import OrderStatus, Role
from raizes.domain.shared.errors import NotFoundError

# Neste MVP só estes destinos são aceitos pela API (PAGO vem do pagamento; CANCELADO fica
# fora do escopo).
ACCEPTED_TARGETS = frozenset({OrderStatus.EM_PREPARO, OrderStatus.PRONTO, OrderStatus.ENTREGUE})


class UpdateOrderStatus:
    def __init__(
        self,
        *,
        orders: OrderRepository,
        audit: AuditRecorder,
        outbox: OutboxWriter,
        uow: UnitOfWork,
    ) -> None:
        self._orders = orders
        self._audit = audit
        self._outbox = outbox
        self._uow = uow

    def execute(
        self, principal: Principal, order_id: UUID, target: OrderStatus, reason: str | None
    ) -> Order:
        if target not in ACCEPTED_TARGETS:
            raise ApplicationValidationError(
                "Status de destino não aceito.",
                detalhes=[
                    {
                        "field": "status",
                        "issue": "informe EM_PREPARO, PRONTO ou ENTREGUE",
                    }
                ],
            )
        order = self._orders.get_for_update(order_id)
        if order is None or (
            principal.role is Role.CLIENTE and order.customer_id != principal.user_id
        ):
            raise NotFoundError("Pedido não encontrado.")

        decision = TransitionPolicy.evaluate(
            role=principal.role,
            current=order.status,
            target=target,
            user_unit_id=principal.unit_id,
            order_unit_id=order.unit_id,
            is_owner=order.customer_id == principal.user_id,
        )
        if not decision:
            raise PermissionDeniedError(
                "Você não pode solicitar esta mudança de status.",
                detalhes=[{"field": "status", "issue": decision.reason}],
            )

        previous = order.status
        order.advance_status(target, principal.user_id, reason)  # 409 TRANSICAO_INVALIDA
        self._orders.save(order)
        self._audit.record(
            AuditEntry(
                action="STATUS_ALTERADO",
                resource_type="PEDIDO",
                resource_id=str(order.id),
                user_id=principal.user_id,
                role=principal.role,
                unit_id=order.unit_id,
                channel=order.channel,
                details={"statusAnterior": previous.value, "statusNovo": target.value},
            )
        )
        self._outbox.add(order.pull_events())
        self._uow.commit()
        return order
