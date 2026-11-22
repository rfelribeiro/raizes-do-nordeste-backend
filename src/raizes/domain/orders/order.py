"""Agregado `Order` (Pedido): itens, histórico de status e tentativas de pagamento.

Regras: RN-01 (nasce AGUARDANDO_PAGAMENTO), RN-03 (máquina de estados), RN-07 (expira em 15 min),
RN-10 (preço congelado no item), RN-11 (canal imutável). Quem pode pedir cada transição (RN-04) é
decidido em `policies.TransitionPolicy`, antes de chamar o agregado.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from raizes.domain.orders.events import (
    OrderCreated,
    OrderStatusChanged,
    PaymentApproved,
    PaymentRefused,
)
from raizes.domain.shared.enums import (
    OrderChannel,
    OrderStatus,
    PaymentAttemptStatus,
    PaymentMethod,
)
from raizes.domain.shared.errors import BusinessRuleViolationError, DomainError
from raizes.domain.shared.events import DomainEvent
from raizes.domain.shared.money import ZERO, to_money

PAYMENT_WINDOW = timedelta(minutes=15)

_S = OrderStatus

# RN-02 e RN-03: única fonte das transições válidas. ENTREGUE e CANCELADO são finais.
ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    _S.AGUARDANDO_PAGAMENTO: frozenset({_S.PAGO, _S.CANCELADO}),
    _S.PAGO: frozenset({_S.EM_PREPARO, _S.CANCELADO}),
    _S.EM_PREPARO: frozenset({_S.PRONTO}),
    _S.PRONTO: frozenset({_S.ENTREGUE}),
    _S.ENTREGUE: frozenset(),
    _S.CANCELADO: frozenset(),
}


def _now() -> datetime:
    return datetime.now(UTC)


def invalid_transition(current: OrderStatus, target: OrderStatus) -> BusinessRuleViolationError:
    return BusinessRuleViolationError(
        f"Transição de {current.value} para {target.value} não é permitida.",
        codigo="TRANSICAO_INVALIDA",
        detalhes=[{"field": "status", "issue": f"{current.value} -> {target.value}"}],
    )


@dataclass(frozen=True, slots=True)
class OrderItem:
    """Item do pedido com preço congelado no momento da criação (RN-10)."""

    product_id: UUID
    quantity: int
    unit_price: Decimal
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise DomainError(
                "Quantidade deve ser maior que zero.",
                codigo="VALIDACAO_FALHOU",
                detalhes=[{"field": "quantidade", "issue": "deve ser maior que zero"}],
            )
        if self.unit_price < 0:
            raise ValueError("preço unitário não pode ser negativo")
        object.__setattr__(self, "unit_price", to_money(self.unit_price))

    @property
    def total(self) -> Decimal:
        return to_money(self.unit_price * self.quantity)


@dataclass(frozen=True, slots=True)
class OrderStatusHistory:
    """Registro append-only de uma mudança de status."""

    previous_status: OrderStatus | None
    new_status: OrderStatus
    user_id: UUID | None
    reason: str | None
    occurred_at: datetime


@dataclass(slots=True)
class PaymentAttempt:
    """Uma chamada do cliente a `POST /pedidos/{id}/pagamentos` (as retentativas ficam em
    `gateway_calls`)."""

    attempt_number: int
    method: PaymentMethod
    amount: Decimal
    status: PaymentAttemptStatus = PaymentAttemptStatus.PENDENTE
    gateway_calls: int = 0
    refusal_reason: str | None = None
    transaction_id: str | None = None
    requested_at: datetime = field(default_factory=_now)
    responded_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)

    def _finish(self, status: PaymentAttemptStatus, calls: int, now: datetime | None) -> None:
        if self.status is not PaymentAttemptStatus.PENDENTE:
            raise BusinessRuleViolationError(
                "A tentativa de pagamento já foi concluída.", codigo="TENTATIVA_JA_CONCLUIDA"
            )
        self.status = status
        self.gateway_calls = calls
        self.responded_at = now or _now()

    def approve(self, transaction_id: str, calls: int = 1, now: datetime | None = None) -> None:
        self._finish(PaymentAttemptStatus.APROVADO, calls, now)
        self.transaction_id = transaction_id

    def refuse(self, reason: str, calls: int = 1, now: datetime | None = None) -> None:
        self._finish(PaymentAttemptStatus.RECUSADO, calls, now)
        self.refusal_reason = reason

    def fail(self, calls: int, now: datetime | None = None) -> None:
        self._finish(PaymentAttemptStatus.FALHA, calls, now)


@dataclass(slots=True)
class Order:
    """Raiz do agregado Pedido."""

    id: UUID
    unit_id: UUID
    customer_id: UUID | None
    creator_id: UUID
    channel: OrderChannel
    status: OrderStatus
    items: list[OrderItem]
    items_value: Decimal
    discount_value: Decimal
    total_value: Decimal
    expires_at: datetime
    created_at: datetime
    order_number: int | None = None
    history: list[OrderStatusHistory] = field(default_factory=list)
    payment_attempts: list[PaymentAttempt] = field(default_factory=list)
    _events: list[DomainEvent] = field(default_factory=list, repr=False)

    @classmethod
    def create(
        cls,
        *,
        unit_id: UUID,
        channel: OrderChannel,
        creator_id: UUID,
        items: Sequence[OrderItem],
        customer_id: UUID | None = None,
        now: datetime | None = None,
    ) -> Order:
        if not items:
            raise DomainError(
                "O pedido precisa de ao menos um item.",
                codigo="VALIDACAO_FALHOU",
                detalhes=[{"field": "itens", "issue": "informe ao menos um item"}],
            )
        created = now or _now()
        items_value = to_money(sum((i.total for i in items), ZERO))
        discount = ZERO  # sem resgate de pontos neste MVP
        order = cls(
            id=uuid4(),
            unit_id=unit_id,
            customer_id=customer_id,
            creator_id=creator_id,
            channel=channel,
            status=OrderStatus.AGUARDANDO_PAGAMENTO,
            items=list(items),
            items_value=items_value,
            discount_value=discount,
            total_value=to_money(items_value - discount),
            expires_at=created + PAYMENT_WINDOW,
            created_at=created,
        )
        order.history.append(OrderStatusHistory(None, order.status, creator_id, None, created))
        order._events.append(
            OrderCreated(
                aggregate_type="pedido",
                aggregate_id=str(order.id),
                occurred_at=created,
                unit_id=unit_id,
                customer_id=customer_id,
                channel=channel.value,
                status=order.status.value,
                total=order.total_value,
            )
        )
        return order

    # --- consultas -----------------------------------------------------------------------

    def is_expired(self, now: datetime | None = None) -> bool:
        return (now or _now()) >= self.expires_at

    def item_total(self, product_id: UUID) -> Decimal:
        return sum((i.total for i in self.items if i.product_id == product_id), ZERO)

    def pull_events(self) -> list[DomainEvent]:
        """Entrega e esvazia os eventos pendentes (o caso de uso os grava na outbox)."""
        events, self._events = self._events, []
        return events

    # --- transições ----------------------------------------------------------------------

    def _transition(
        self, target: OrderStatus, user_id: UUID | None, reason: str | None, now: datetime | None
    ) -> None:
        if target not in ALLOWED_TRANSITIONS[self.status]:
            raise invalid_transition(self.status, target)
        when = now or _now()
        previous, self.status = self.status, target
        self.history.append(OrderStatusHistory(previous, target, user_id, reason, when))
        self._events.append(
            OrderStatusChanged(
                aggregate_type="pedido",
                aggregate_id=str(self.id),
                occurred_at=when,
                unit_id=self.unit_id,
                channel=self.channel.value,
                previous_status=previous.value,
                new_status=target.value,
            )
        )

    def advance_status(
        self,
        target: OrderStatus,
        user_id: UUID,
        reason: str | None = None,
        now: datetime | None = None,
    ) -> None:
        """Mudança manual de status. PAGO só pelo resultado do pagamento (`mark_paid`)."""
        if target is OrderStatus.PAGO:
            raise invalid_transition(self.status, target)
        self._transition(target, user_id, reason, now)

    def cancel(self, user_id: UUID, reason: str | None = None, now: datetime | None = None) -> None:
        """RN-02: só de AGUARDANDO_PAGAMENTO ou PAGO."""
        self._transition(OrderStatus.CANCELADO, user_id, reason, now)

    # --- pagamento -----------------------------------------------------------------------

    def request_payment(self, method: PaymentMethod, now: datetime | None = None) -> PaymentAttempt:
        """Abre uma tentativa PENDENTE; só com o pedido em AGUARDANDO_PAGAMENTO."""
        if self.status is not OrderStatus.AGUARDANDO_PAGAMENTO:
            raise BusinessRuleViolationError(
                "O pedido não está aguardando pagamento.",
                codigo="PEDIDO_FORA_DE_AGUARDANDO_PAGAMENTO",
                detalhes=[{"field": "status", "issue": self.status.value}],
            )
        attempt = PaymentAttempt(
            attempt_number=len(self.payment_attempts) + 1,
            method=method,
            amount=self.total_value,
            requested_at=now or _now(),
        )
        self.payment_attempts.append(attempt)
        return attempt

    def mark_paid(
        self,
        attempt: PaymentAttempt,
        transaction_id: str,
        calls: int = 1,
        now: datetime | None = None,
    ) -> None:
        """Pagamento aprovado: AGUARDANDO_PAGAMENTO -> PAGO (RN-01, RN-04)."""
        if self.status is not OrderStatus.AGUARDANDO_PAGAMENTO:
            raise invalid_transition(self.status, OrderStatus.PAGO)
        when = now or _now()
        attempt.approve(transaction_id, calls, when)
        self._transition(OrderStatus.PAGO, None, "pagamento aprovado", when)
        self._events.append(
            PaymentApproved(
                aggregate_type="pedido",
                aggregate_id=str(self.id),
                occurred_at=when,
                unit_id=self.unit_id,
                channel=self.channel.value,
                method=attempt.method.value,
                amount=attempt.amount,
                attempt_number=attempt.attempt_number,
            )
        )

    def register_refusal(
        self, attempt: PaymentAttempt, reason: str, calls: int = 1, now: datetime | None = None
    ) -> None:
        """Recusa (RN-01): o pedido continua em AGUARDANDO_PAGAMENTO, com o motivo guardado."""
        when = now or _now()
        attempt.refuse(reason, calls, when)
        self._events.append(
            PaymentRefused(
                aggregate_type="pedido",
                aggregate_id=str(self.id),
                occurred_at=when,
                unit_id=self.unit_id,
                channel=self.channel.value,
                method=attempt.method.value,
                amount=attempt.amount,
                attempt_number=attempt.attempt_number,
                reason=reason,
            )
        )

    def register_failure(
        self, attempt: PaymentAttempt, calls: int, now: datetime | None = None
    ) -> None:
        """Timeout esgotado (D-051): tentativa FALHA, pedido segue em AGUARDANDO_PAGAMENTO."""
        attempt.fail(calls, now)
