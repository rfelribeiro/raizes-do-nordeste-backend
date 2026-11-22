"""RNF-11: criações simultâneas disputando o mesmo estoque nunca o deixam negativo."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import ModuleType

import pytest
from fastapi.testclient import TestClient

from raizes.api.composition.payments import get_payment_gateway
from raizes.main import create_app
from tests.integration.helpers import execute, post_order, query, scalar

pytestmark = pytest.mark.integration

Headers = Callable[[str], dict[str, str]]


def _set_stock(seeded: ModuleType, quantity: int) -> None:
    execute(
        "UPDATE estoques SET qtd_disponivel = :q WHERE id_produto = :p AND id_unidade = :u",
        q=quantity,
        p=seeded.PRODUCT_CARNE_SOL_ID,
        u=seeded.UNIT_1_ID,
    )


def _race(seeded: ModuleType, headers: dict[str, str], attempts: int) -> list[int]:
    app = create_app()
    app.dependency_overrides[get_payment_gateway] = lambda: None
    barrier = Barrier(attempts)

    def attempt(_: int) -> int:
        with TestClient(app) as test_client:
            barrier.wait()
            response = post_order(
                test_client, headers, seeded, items=[(seeded.PRODUCT_CARNE_SOL_ID, 1)]
            )
            return response.status_code

    with ThreadPoolExecutor(max_workers=attempts) as pool:
        return list(pool.map(attempt, range(attempts)))


def test_duas_criacoes_disputam_o_ultimo_item(as_user: Headers, seeded: ModuleType) -> None:
    _set_stock(seeded, 1)

    statuses = _race(seeded, as_user("cliente"), attempts=2)

    assert sorted(statuses) == [201, 409]
    stock = query(
        "SELECT qtd_disponivel, qtd_reservada FROM estoques WHERE id_produto = :p AND id_unidade = :u",  # noqa: E501
        p=seeded.PRODUCT_CARNE_SOL_ID,
        u=seeded.UNIT_1_ID,
    )[0]
    assert (stock.qtd_disponivel, stock.qtd_reservada) == (0, 1)
    assert scalar("SELECT count(*) FROM pedidos") == 1
    assert scalar("SELECT count(*) FROM movimentacoes_estoque WHERE tipo = 'RESERVA'") == 1


def test_varias_criacoes_simultaneas_nao_vendem_mais_que_o_estoque(
    as_user: Headers, seeded: ModuleType
) -> None:
    _set_stock(seeded, 3)

    statuses = _race(seeded, as_user("cliente"), attempts=8)

    assert statuses.count(201) == 3
    assert statuses.count(409) == 5
    stock = query(
        "SELECT qtd_disponivel, qtd_reservada FROM estoques WHERE id_produto = :p AND id_unidade = :u",  # noqa: E501
        p=seeded.PRODUCT_CARNE_SOL_ID,
        u=seeded.UNIT_1_ID,
    )[0]
    assert (stock.qtd_disponivel, stock.qtd_reservada) == (0, 3)
    assert scalar("SELECT count(*) FROM pedidos") == 3
