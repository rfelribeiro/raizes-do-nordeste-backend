"""UC-05 Solicitar Pagamento (D-054): duas transações curtas, com a chamada ao gateway FORA delas.

T1 trava o pedido, valida e grava a tentativa PENDENTE. O gateway é chamado sem transação aberta.
T2 trava o pedido de novo e grava o resultado (pedido pago + baixa de estoque, recusa ou falha).
"""

import logging
from dataclasses import dataclass
from uuid import UUID

from raizes.application.errors import ConflictError, DependencyTimeoutError, PermissionDeniedError
from raizes.application.ports.audit import AuditEntry, AuditRecorder
from raizes.application.ports.orders import OrderRepository
from raizes.application.ports.outbox import OutboxWriter
from raizes.application.ports.payment_gateway import GatewayResult, PaymentGateway
from raizes.application.ports.stock import StockRepository
from raizes.application.ports.unit_of_work import UnitOfWork
from raizes.application.principal import Principal
from raizes.domain.orders.order import Order, PaymentAttempt
from raizes.domain.shared.enums import OrderStatus, PaymentAttemptStatus, PaymentMethod, Role
from raizes.domain.shared.errors import BusinessRuleViolationError, NotFoundError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PaymentOutcome:
    attempt: PaymentAttempt
    order_status: OrderStatus


class RequestPayment:
    def __init__(
        self,
        *,
        orders: OrderRepository,
        stock: StockRepository,
        gateway: PaymentGateway,
        audit: AuditRecorder,
        outbox: OutboxWriter,
        uow: UnitOfWork,
    ) -> None:
        self._orders = orders
        self._stock = stock
        self._gateway = gateway
        self._audit = audit
        self._outbox = outbox
        self._uow = uow

    def execute(
        self, principal: Principal, order_id: UUID, method: PaymentMethod, token: str
    ) -> PaymentOutcome:
        if principal.role is not Role.CLIENTE:
            raise PermissionDeniedError("Só o cliente dono do pedido solicita o pagamento.")

        # --- T1: valida e registra a tentativa PENDENTE ---------------------------------------
        order = self._orders.get_for_update(order_id)
        if order is None or order.customer_id != principal.user_id:
            raise NotFoundError("Pedido não encontrado.")
        if any(a.status is PaymentAttemptStatus.PENDENTE for a in order.payment_attempts):
            raise ConflictError(
                "Já existe um pagamento em andamento para este pedido.",
                codigo="PAGAMENTO_EM_ANDAMENTO",
            )
        if order.status is OrderStatus.AGUARDANDO_PAGAMENTO and order.is_expired():
            raise BusinessRuleViolationError(
                "O prazo para pagamento do pedido expirou.", codigo="PEDIDO_EXPIRADO"
            )
        attempt = order.request_payment(method)  # 409 se não estiver aguardando pagamento
        self._orders.save(order)
        self._uow.commit()
        attempt_id, amount = attempt.id, attempt.amount

        # --- chamada externa, sem transação aberta ---------------------------------------------
        try:
            result = self._gateway.charge(order_id, amount, method, token)
        except Exception:
            logger.exception("Falha inesperada ao chamar o gateway de pagamento")
            result = GatewayResult(status=PaymentAttemptStatus.FALHA, calls=1)

        # --- T2: grava o resultado ---------------------------------------------------------------
        order = self._orders.get_for_update(order_id)
        if order is None:  # pragma: no cover - pedidos não são apagados
            raise NotFoundError("Pedido não encontrado.")
        attempt = next(a for a in order.payment_attempts if a.id == attempt_id)

        if order.status is not OrderStatus.AGUARDANDO_PAGAMENTO:
            self._record_divergence(principal, order, attempt, result)
            raise ConflictError(
                "O pedido deixou de aguardar pagamento durante a cobrança.",
                codigo="PAGAMENTO_DIVERGENTE",
            )

        if result.status is PaymentAttemptStatus.APROVADO:
            order.mark_paid(attempt, result.transaction_id or "", result.calls)
            self._write_off_stock(principal, order)
            self._audit_attempt("PAGAMENTO_APROVADO", principal, order, attempt)
        elif result.status is PaymentAttemptStatus.RECUSADO:
            reason = result.refusal_reason or "Pagamento recusado"
            order.register_refusal(attempt, reason, result.calls)
            self._audit_attempt("PAGAMENTO_RECUSADO", principal, order, attempt)
        else:
            order.register_failure(attempt, result.calls)
        self._orders.save(order)
        self._outbox.add(order.pull_events())
        self._uow.commit()

        if attempt.status is PaymentAttemptStatus.FALHA:
            raise DependencyTimeoutError("O gateway de pagamento não respondeu a tempo.")
        return PaymentOutcome(attempt=attempt, order_status=order.status)

    def _write_off_stock(self, principal: Principal, order: Order) -> None:
        product_ids = sorted(i.product_id for i in order.items)
        stocks = self._stock.get_for_update(order.unit_id, product_ids)
        for item in sorted(order.items, key=lambda i: i.product_id):
            stock = stocks[item.product_id]
            movement = stock.write_off(item.quantity, order.id, principal.user_id)
            self._stock.save(stock, [movement])

    def _audit_attempt(
        self, action: str, principal: Principal, order: Order, attempt: PaymentAttempt
    ) -> None:
        self._audit.record(
            AuditEntry(
                action=action,
                resource_type="PEDIDO",
                resource_id=str(order.id),
                user_id=principal.user_id,
                role=principal.role,
                unit_id=order.unit_id,
                channel=order.channel,
                details={
                    "numeroTentativa": attempt.attempt_number,
                    "formaPagamento": attempt.method.value,
                    "valor": str(attempt.amount),
                    "qtdChamadasGateway": attempt.gateway_calls,
                },
            )
        )

    def _record_divergence(
        self, principal: Principal, order: Order, attempt: PaymentAttempt, result: GatewayResult
    ) -> None:
        """D12: grava a tentativa com o resultado do gateway e audita para conciliação."""
        if result.status is PaymentAttemptStatus.APROVADO:
            attempt.approve(result.transaction_id or "", result.calls)
        elif result.status is PaymentAttemptStatus.RECUSADO:
            attempt.refuse(result.refusal_reason or "Pagamento recusado", result.calls)
        else:
            attempt.fail(result.calls)
        self._orders.save(order)
        self._audit.record(
            AuditEntry(
                action="PAGAMENTO_DIVERGENTE",
                resource_type="PEDIDO",
                resource_id=str(order.id),
                user_id=principal.user_id,
                role=principal.role,
                unit_id=order.unit_id,
                channel=order.channel,
                details={
                    "numeroTentativa": attempt.attempt_number,
                    "resultadoGateway": result.status.value,
                    "statusPedido": order.status.value,
                },
            )
        )
        self._uow.commit()
