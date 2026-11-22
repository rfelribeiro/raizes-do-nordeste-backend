from uuid import uuid4

import pytest

from raizes.domain.shared.enums import StockMovementType
from raizes.domain.shared.errors import BusinessRuleViolationError, DomainError
from raizes.domain.stock.stock import Stock

ORDER = uuid4()
USER = uuid4()


def make_stock(available: int = 10, reserved: int = 0) -> Stock:
    return Stock(uuid4(), uuid4(), available, reserved)


def test_reserve_moves_available_to_reserved() -> None:
    stock = make_stock()
    movement = stock.reserve(4, ORDER, USER)
    assert (stock.available, stock.reserved) == (6, 4)
    assert movement.type is StockMovementType.RESERVA
    assert movement.quantity == 4
    assert movement.order_id == ORDER
    assert movement.user_id == USER
    assert (movement.unit_id, movement.product_id) == (stock.unit_id, stock.product_id)


def test_reserve_insufficient_is_409_with_available() -> None:
    stock = make_stock(3)
    with pytest.raises(BusinessRuleViolationError) as exc:
        stock.reserve(4, ORDER)
    assert exc.value.codigo == "ESTOQUE_INSUFICIENTE"
    assert "disponível 3" in exc.value.detalhes[0]["issue"]
    assert (stock.available, stock.reserved) == (3, 0)


def test_reserve_exact_available() -> None:
    stock = make_stock(3)
    stock.reserve(3, ORDER)
    assert (stock.available, stock.reserved) == (0, 3)


def test_release_returns_reservation() -> None:
    stock = make_stock(6, 4)
    movement = stock.release(4, ORDER)
    assert (stock.available, stock.reserved) == (10, 0)
    assert movement.type is StockMovementType.LIBERACAO


def test_write_off_consumes_reservation() -> None:
    stock = make_stock(6, 4)
    movement = stock.write_off(4, ORDER)
    assert (stock.available, stock.reserved) == (6, 0)
    assert movement.type is StockMovementType.BAIXA


@pytest.mark.parametrize("method", ["release", "write_off"])
def test_cannot_exceed_reserved(method: str) -> None:
    stock = make_stock(6, 2)
    with pytest.raises(BusinessRuleViolationError):
        getattr(stock, method)(3, ORDER)
    assert (stock.available, stock.reserved) == (6, 2)


def test_register_entry() -> None:
    stock = make_stock(0)
    movement = stock.register_entry(5, USER, "compra")
    assert stock.available == 5
    assert movement.type is StockMovementType.ENTRADA
    assert movement.reason == "compra"


def test_adjust_positive_and_negative() -> None:
    stock = make_stock(5)
    up = stock.adjust(2, positive=True, reason="cancelamento do pedido 7", user_id=USER)
    assert stock.available == 7
    assert up.type is StockMovementType.AJUSTE_POSITIVO
    down = stock.adjust(3, positive=False, reason="perda")
    assert stock.available == 4
    assert down.type is StockMovementType.AJUSTE_NEGATIVO
    with pytest.raises(BusinessRuleViolationError):
        stock.adjust(5, positive=False, reason="perda")


def test_adjust_requires_reason() -> None:
    with pytest.raises(DomainError) as exc:
        make_stock().adjust(1, positive=True, reason=" ")
    assert exc.value.codigo == "VALIDACAO_FALHOU"


@pytest.mark.parametrize("quantity", [0, -1])
def test_quantity_must_be_positive(quantity: int) -> None:
    stock = make_stock(5, 5)
    for call in (
        lambda: stock.reserve(quantity, ORDER),
        lambda: stock.release(quantity, ORDER),
        lambda: stock.write_off(quantity, ORDER),
        lambda: stock.register_entry(quantity),
        lambda: stock.adjust(quantity, positive=True, reason="x"),
    ):
        with pytest.raises(DomainError):
            call()
