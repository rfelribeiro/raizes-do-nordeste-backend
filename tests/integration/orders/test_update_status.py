"""PATCH /pedidos/{id}/status (UC-06): perfil (403) antes da máquina de estados (409)."""

from collections.abc import Callable
from types import ModuleType
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from tests.integration.helpers import API, pay, post_order, scalar

pytestmark = pytest.mark.integration

Headers = Callable[[str], dict[str, str]]


def _patch(client: TestClient, headers: dict[str, str], order_id: str, status: str) -> Response:
    return client.patch(
        f"{API}/pedidos/{order_id}/status", json={"status": status}, headers=headers
    )  # noqa: E501


@pytest.fixture
def paid_order(client: TestClient, as_user: Headers, seeded: ModuleType) -> str:
    order_id = post_order(client, as_user("cliente"), seeded).json()["id"]
    assert pay(client, as_user("cliente"), order_id).status_code == 201
    return str(order_id)


def test_fluxo_completo_de_status(client: TestClient, as_user: Headers, paid_order: str) -> None:
    em_preparo = _patch(client, as_user("cozinha"), paid_order, "EM_PREPARO")
    pronto = _patch(client, as_user("cozinha"), paid_order, "PRONTO")
    entregue = _patch(client, as_user("atendente"), paid_order, "ENTREGUE")

    assert [r.status_code for r in (em_preparo, pronto, entregue)] == [200, 200, 200]
    assert entregue.json()["status"] == "ENTREGUE"
    # criado + pago + 3 mudanças manuais
    assert scalar("SELECT count(*) FROM historico_status_pedido") == 5
    assert scalar("SELECT count(*) FROM auditoria WHERE acao = 'STATUS_ALTERADO'") == 3
    assert (
        scalar("SELECT count(*) FROM outbox_eventos WHERE tipo_evento = 'status_pedido_alterado'")
        == 4  # PAGO + 3 manuais
    )


def test_gerente_avanca_na_propria_unidade(
    client: TestClient, as_user: Headers, paid_order: str
) -> None:
    assert _patch(client, as_user("gerente"), paid_order, "EM_PREPARO").status_code == 200


def test_transicao_invalida_409(client: TestClient, as_user: Headers, paid_order: str) -> None:
    response = _patch(client, as_user("cozinha"), paid_order, "PRONTO")  # PAGO -> PRONTO

    assert response.status_code == 409
    assert response.json()["error"] == "TRANSICAO_INVALIDA"
    assert scalar("SELECT status FROM pedidos") == "PAGO"


def test_gerente_pedindo_pronto_num_pedido_pago_409(
    client: TestClient, as_user: Headers, paid_order: str
) -> None:
    assert _patch(client, as_user("gerente"), paid_order, "PRONTO").status_code == 409


def test_saida_de_estado_final_409(client: TestClient, as_user: Headers, paid_order: str) -> None:
    for user, status in (
        ("cozinha", "EM_PREPARO"),
        ("cozinha", "PRONTO"),
        ("atendente", "ENTREGUE"),
    ):  # noqa: E501
        assert _patch(client, as_user(user), paid_order, status).status_code == 200

    response = _patch(client, as_user("cozinha"), paid_order, "PRONTO")

    assert response.status_code == 409


def test_pedido_ainda_nao_pago_409(
    client: TestClient, as_user: Headers, seeded: ModuleType
) -> None:
    order_id = post_order(client, as_user("cliente"), seeded).json()["id"]

    response = _patch(client, as_user("cozinha"), order_id, "EM_PREPARO")

    assert response.status_code == 409


def test_perfil_errado_para_o_status_403(
    client: TestClient, as_user: Headers, paid_order: str
) -> None:
    for user in ("cozinha", "cliente", "admin"):
        status = "ENTREGUE"
        response = _patch(client, as_user(user), paid_order, status)
        assert response.status_code == 403, user
    assert _patch(client, as_user("atendente"), paid_order, "EM_PREPARO").status_code == 403
    assert scalar("SELECT status FROM pedidos") == "PAGO"


def test_gerente_de_outra_unidade_403(
    client: TestClient, as_user: Headers, paid_order: str
) -> None:
    assert _patch(client, as_user("gerente2"), paid_order, "EM_PREPARO").status_code == 403


@pytest.mark.parametrize("status", ["PAGO", "CANCELADO", "AGUARDANDO_PAGAMENTO", "INVENTADO"])
def test_status_nao_aceito_422(
    client: TestClient, as_user: Headers, paid_order: str, status: str
) -> None:
    response = _patch(client, as_user("gerente"), paid_order, status)

    assert response.status_code == 422


def test_pedido_inexistente_404(client: TestClient, as_user: Headers, seeded: ModuleType) -> None:
    assert _patch(client, as_user("cozinha"), str(uuid4()), "EM_PREPARO").status_code == 404
