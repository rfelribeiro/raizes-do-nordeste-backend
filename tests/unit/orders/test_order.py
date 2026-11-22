from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from raizes.domain.orders.order import ALLOWED_TRANSITIONS, Order, OrderItem, PaymentAttempt
from raizes.domain.shared.enums import (
    OrderChannel,
    OrderStatus,
    PaymentAttemptStatus,
    PaymentMethod,
)
from raizes.domain.shared.errors import BusinessRuleViolationError, DomainError
from raizes.domain.shared.money import to_money

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
USER = uuid4()


def make_order(status: OrderStatus = OrderStatus.AGUARDANDO_PAGAMENTO) -> Order:
    order = Order.create(
        unit_id=uuid4(),
        channel=OrderChannel.APP,
        creator_id=USER,
        customer_id=USER,
        items=[
            OrderItem(uuid4(), 2, Decimal("12.50")),
            OrderItem(uuid4(), 1, Decimal("7.90")),
        ],
        now=NOW,
    )
    order.status = status
    return order


def test_create_totals_and_defaults() -> None:
    order = make_order()
    assert order.status is OrderStatus.AGUARDANDO_PAGAMENTO
    assert order.items_value == Decimal("32.90")
    assert order.discount_value == Decimal("0.00")
    assert order.total_value == Decimal("32.90")
    assert order.expires_at == NOW + timedelta(minutes=15)
    assert [h.new_status for h in order.history] == [OrderStatus.AGUARDANDO_PAGAMENTO]
    assert [e.event_type for e in order.pull_events()] == ["pedido_criado"]
    assert order.pull_events() == []


def test_item_total_and_frozen_price() -> None:
    item = OrderItem(uuid4(), 3, Decimal("4.5"))
    assert item.unit_price == Decimal("4.50")
    assert item.total == Decimal("13.50")
    with pytest.raises(AttributeError):
        item.unit_price = Decimal("1.00")  # type: ignore[misc]


def test_money_rounds_half_even() -> None:
    assert to_money("0.125") == Decimal("0.12")
    assert to_money("0.135") == Decimal("0.14")
    with pytest.raises(TypeError):
        to_money(1.5)  # type: ignore[arg-type]


def test_create_requires_items_and_positive_quantity() -> None:
    with pytest.raises(DomainError) as exc:
        Order.create(unit_id=uuid4(), channel=OrderChannel.APP, creator_id=USER, items=[])
    assert exc.value.codigo == "VALIDACAO_FALHOU"
    with pytest.raises(DomainError):
        OrderItem(uuid4(), 0, Decimal("1.00"))


def test_is_expired() -> None:
    order = make_order()
    assert not order.is_expired(NOW + timedelta(minutes=14))
    assert order.is_expired(NOW + timedelta(minutes=15))


ALL = list(OrderStatus)


@pytest.mark.parametrize("current", ALL)
@pytest.mark.parametrize("target", ALL)
def test_full_transition_table(current: OrderStatus, target: OrderStatus) -> None:
    order = make_order(current)
    order.pull_events()
    valid = target in ALLOWED_TRANSITIONS[current] and target is not OrderStatus.PAGO
    if valid:
        order.advance_status(target, USER, now=NOW)
        assert order.status is target
        assert order.history[-1].previous_status is current
        assert order.history[-1].new_status is target
        events = order.pull_events()
        assert [e.event_type for e in events] == ["status_pedido_alterado"]
    else:
        with pytest.raises(BusinessRuleViolationError) as exc:
            order.advance_status(target, USER, now=NOW)
        assert exc.value.codigo == "TRANSICAO_INVALIDA"
        assert order.status is current
        assert len(order.history) == 1


@pytest.mark.parametrize("current", [s for s in ALL if s is not OrderStatus.AGUARDANDO_PAGAMENTO])
def test_mark_paid_only_from_awaiting_payment(current: OrderStatus) -> None:
    order = make_order(current)
    pending = PaymentAttempt(1, PaymentMethod.PIX, order.total_value)
    with pytest.raises(BusinessRuleViolationError) as exc:
        order.mark_paid(pending, "txn_1")
    assert exc.value.codigo == "TRANSICAO_INVALIDA"


def test_cancel_only_before_preparation() -> None:
    for status in (OrderStatus.AGUARDANDO_PAGAMENTO, OrderStatus.PAGO):
        order = make_order(status)
        order.cancel(USER, "desistência")
        assert order.status is OrderStatus.CANCELADO
        assert order.history[-1].reason == "desistência"
    for status in (OrderStatus.EM_PREPARO, OrderStatus.PRONTO, OrderStatus.ENTREGUE):
        with pytest.raises(BusinessRuleViolationError):
            make_order(status).cancel(USER)


def test_payment_approved_flow() -> None:
    order = make_order()
    order.pull_events()
    attempt = order.request_payment(PaymentMethod.PIX, now=NOW)
    assert attempt.attempt_number == 1
    assert attempt.amount == Decimal("32.90")
    assert attempt.status is PaymentAttemptStatus.PENDENTE
    order.mark_paid(attempt, "txn_abc", calls=1, now=NOW)
    assert order.status is OrderStatus.PAGO
    assert attempt.status is PaymentAttemptStatus.APROVADO
    assert attempt.transaction_id == "txn_abc"
    types = [e.event_type for e in order.pull_events()]
    assert types == ["status_pedido_alterado", "pagamento_aprovado"]


def test_payment_refused_keeps_order_awaiting() -> None:
    order = make_order()
    order.pull_events()
    attempt = order.request_payment(PaymentMethod.CREDITO)
    order.register_refusal(attempt, "sem saldo", calls=1)
    assert order.status is OrderStatus.AGUARDANDO_PAGAMENTO
    assert attempt.status is PaymentAttemptStatus.RECUSADO
    assert attempt.refusal_reason == "sem saldo"
    assert [e.event_type for e in order.pull_events()] == ["pagamento_recusado"]
    second = order.request_payment(PaymentMethod.PIX)
    assert second.attempt_number == 2


def test_payment_failure_after_timeouts() -> None:
    order = make_order()
    attempt = order.request_payment(PaymentMethod.DEBITO)
    order.register_failure(attempt, calls=3)
    assert attempt.status is PaymentAttemptStatus.FALHA
    assert attempt.gateway_calls == 3
    assert order.status is OrderStatus.AGUARDANDO_PAGAMENTO


def test_request_payment_outside_awaiting_is_409() -> None:
    with pytest.raises(BusinessRuleViolationError):
        make_order(OrderStatus.PAGO).request_payment(PaymentMethod.PIX)


def test_attempt_cannot_be_finished_twice() -> None:
    order = make_order()
    attempt = order.request_payment(PaymentMethod.PIX)
    order.register_refusal(attempt, "x")
    with pytest.raises(BusinessRuleViolationError):
        attempt.approve("txn")


def test_event_payloads_have_no_pii() -> None:
    order = make_order()
    attempt = order.request_payment(PaymentMethod.PIX)
    order.mark_paid(attempt, "txn")
    for event in order.pull_events():
        text = str(event.payload()).lower()
        for forbidden in ("email", "nome", "cpf", "token", "senha"):
            assert forbidden not in text
