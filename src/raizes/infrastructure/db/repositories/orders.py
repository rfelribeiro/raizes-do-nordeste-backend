"""Persistência do agregado Pedido (pedido, itens, histórico e tentativas de pagamento)."""

from uuid import UUID, uuid4

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session, selectinload

from raizes.application.ports.orders import OrderFilter
from raizes.domain.orders.order import Order, OrderItem, OrderStatusHistory, PaymentAttempt
from raizes.domain.shared.enums import (
    OrderChannel,
    OrderStatus,
    PaymentAttemptStatus,
    PaymentMethod,
)
from raizes.infrastructure.db.models import orders as models


class SqlAlchemyOrderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        # Quantos registros de histórico já estão no banco (o histórico é append-only).
        self._persisted_history: dict[UUID, int] = {}

    # --- leitura ---------------------------------------------------------------------------

    def get(self, order_id: UUID) -> Order | None:
        return self._load(order_id, lock=False)

    def get_for_update(self, order_id: UUID) -> Order | None:
        """Trava a linha do pedido (SELECT ... FOR UPDATE) e relê o estado do banco."""
        return self._load(order_id, lock=True)

    def _load(self, order_id: UUID, *, lock: bool) -> Order | None:
        stmt = (
            select(models.Order)
            .where(models.Order.id == order_id)
            .options(selectinload(models.Order.items))
            .execution_options(populate_existing=True)
        )
        if lock:
            stmt = stmt.with_for_update(of=models.Order)
        row = self._session.scalars(stmt).one_or_none()
        if row is None:
            return None
        history = self._session.scalars(
            select(models.OrderStatusHistory)
            .where(models.OrderStatusHistory.order_id == order_id)
            .order_by(models.OrderStatusHistory.occurred_at, models.OrderStatusHistory.id)
            .execution_options(populate_existing=True)
        ).all()
        attempts = self._session.scalars(
            select(models.PaymentAttempt)
            .where(models.PaymentAttempt.order_id == order_id)
            .order_by(models.PaymentAttempt.attempt_number)
            .execution_options(populate_existing=True)
        ).all()
        self._persisted_history[order_id] = len(history)
        order = self._to_domain(row)
        order.history = [self._history_to_domain(h) for h in history]
        order.payment_attempts = [self._attempt_to_domain(a) for a in attempts]
        return order

    def list(self, filter: OrderFilter, page: int, limit: int) -> tuple[list[Order], int]:
        """Página de pedidos (mais recentes primeiro). Vem com itens; sem histórico/tentativas."""
        conditions: list[ColumnElement[bool]] = []
        if filter.channel is not None:
            conditions.append(models.Order.channel == filter.channel.value)
        if filter.status is not None:
            conditions.append(models.Order.status == filter.status.value)
        if filter.unit_id is not None:
            conditions.append(models.Order.unit_id == filter.unit_id)
        if filter.customer_id is not None:
            conditions.append(models.Order.customer_id == filter.customer_id)
        total = (
            self._session.scalar(select(func.count()).select_from(models.Order).where(*conditions))
            or 0
        )
        rows = self._session.scalars(
            select(models.Order)
            .where(*conditions)
            .options(selectinload(models.Order.items))
            .order_by(models.Order.created_at.desc(), models.Order.id)
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
        return [self._to_domain(r) for r in rows], total

    # --- escrita ---------------------------------------------------------------------------

    def add(self, order: Order) -> None:
        row = models.Order(
            id=order.id,
            unit_id=order.unit_id,
            customer_id=order.customer_id,
            created_by_id=order.creator_id,
            channel=order.channel.value,
            status=order.status.value,
            items_total=order.items_value,
            discount_total=order.discount_value,
            total=order.total_value,
            expires_at=order.expires_at,
            created_at=order.created_at,
        )
        row.items = [
            models.OrderItem(
                id=i.id,
                order_id=order.id,
                product_id=i.product_id,
                quantity=i.quantity,
                unit_price=i.unit_price,
                line_total=i.total,
            )
            for i in order.items
        ]
        self._session.add(row)
        self._session.flush()  # materializa o pedido (FKs dos demais) e o número gerado pelo banco
        if row.order_number is None:  # pragma: no cover - o RETURNING costuma trazê-lo
            self._session.refresh(row, ["order_number"])
        order.order_number = row.order_number
        self._persisted_history[order.id] = 0
        self._append_history(order)
        self._sync_attempts(order)

    def save(self, order: Order) -> None:
        row = self._session.get(models.Order, order.id)
        if row is None:
            raise LookupError("pedido inexistente: use add() para pedidos novos")
        row.status = order.status.value
        row.updated_at = func.now()
        self._append_history(order)
        self._sync_attempts(order)
        self._session.flush()

    def _append_history(self, order: Order) -> None:
        persisted = self._persisted_history.get(order.id, 0)
        for h in order.history[persisted:]:
            self._session.add(
                models.OrderStatusHistory(
                    id=uuid4(),
                    order_id=order.id,
                    previous_status=h.previous_status.value if h.previous_status else None,
                    new_status=h.new_status.value,
                    user_id=h.user_id,
                    reason=h.reason,
                    occurred_at=h.occurred_at,
                )
            )
        self._persisted_history[order.id] = len(order.history)

    def _sync_attempts(self, order: Order) -> None:
        for a in order.payment_attempts:
            row = self._session.get(models.PaymentAttempt, a.id)
            if row is None:
                row = models.PaymentAttempt(id=a.id, order_id=order.id)
                self._session.add(row)
            row.attempt_number = a.attempt_number
            row.method = a.method.value
            row.status = a.status.value
            row.amount = a.amount
            row.gateway_calls = max(1, a.gateway_calls)  # CHECK >= 1; PENDENTE ainda não chamou
            row.decline_reason = a.refusal_reason
            row.gateway_transaction_id = a.transaction_id
            row.requested_at = a.requested_at
            row.responded_at = a.responded_at
            row.updated_at = func.now()

    # --- mapeamento ORM -> domínio -----------------------------------------------------------

    @staticmethod
    def _to_domain(row: models.Order) -> Order:
        return Order(
            id=row.id,
            unit_id=row.unit_id,
            customer_id=row.customer_id,
            creator_id=row.created_by_id,
            channel=OrderChannel(row.channel),
            status=OrderStatus(row.status),
            items=[
                OrderItem(
                    id=i.id, product_id=i.product_id, quantity=i.quantity, unit_price=i.unit_price
                )
                for i in row.items
            ],
            items_value=row.items_total,
            discount_value=row.discount_total,
            total_value=row.total,
            expires_at=row.expires_at,
            created_at=row.created_at,
            order_number=row.order_number,
        )

    @staticmethod
    def _history_to_domain(row: models.OrderStatusHistory) -> OrderStatusHistory:
        return OrderStatusHistory(
            previous_status=OrderStatus(row.previous_status) if row.previous_status else None,
            new_status=OrderStatus(row.new_status),
            user_id=row.user_id,
            reason=row.reason,
            occurred_at=row.occurred_at,
        )

    @staticmethod
    def _attempt_to_domain(row: models.PaymentAttempt) -> PaymentAttempt:
        return PaymentAttempt(
            id=row.id,
            attempt_number=row.attempt_number,
            method=PaymentMethod(row.method),
            amount=row.amount,
            status=PaymentAttemptStatus(row.status),
            gateway_calls=row.gateway_calls,
            refusal_reason=row.decline_reason,
            transaction_id=row.gateway_transaction_id,
            requested_at=row.requested_at,
            responded_at=row.responded_at,
        )
