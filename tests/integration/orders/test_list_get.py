"""GET /pedidos e GET /pedidos/{id} (RF-08): filtros, paginação e escopo por perfil."""

from collections.abc import Callable
from types import ModuleType
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from tests.integration.helpers import API, post_order

pytestmark = pytest.mark.integration

Headers = Callable[[str], dict[str, str]]


@pytest.fixture
def orders(client: TestClient, as_user: Headers, seeded: ModuleType) -> dict[str, str]:
    """Quatro pedidos: cliente 1 (APP, unidade 1), cliente 2 (WEB, unidade 1), balcão (unidade 1)
    e totem (unidade 2, feito pelo gerente 2)."""
    made = {
        "c1": post_order(client, as_user("cliente"), seeded, channel="APP"),
        "c2": post_order(client, as_user("cliente2"), seeded, channel="WEB"),
        "balcao": post_order(client, as_user("atendente"), seeded, channel="BALCAO"),
        "u2": post_order(
            client,
            as_user("gerente2"),
            seeded,
            channel="TOTEM",
            unit=seeded.UNIT_2_ID,
            items=[(seeded.PRODUCT_CUSCUZ_ID, 1)],
        ),
    }
    assert all(r.status_code == 201 for r in made.values())
    return {name: r.json()["id"] for name, r in made.items()}


def _ids(response: Response) -> set[str]:
    return {o["id"] for o in response.json()["items"]}


def test_cliente_ve_so_os_seus(
    client: TestClient, as_user: Headers, orders: dict[str, str]
) -> None:  # noqa: E501
    response = client.get(f"{API}/pedidos", headers=as_user("cliente"))

    assert response.status_code == 200
    assert _ids(response) == {orders["c1"]}
    assert response.json()["total"] == 1


def test_colaborador_ve_so_a_sua_unidade(
    client: TestClient, as_user: Headers, orders: dict[str, str]
) -> None:
    gerente = client.get(f"{API}/pedidos", headers=as_user("gerente"))
    gerente2 = client.get(f"{API}/pedidos", headers=as_user("gerente2"))
    cozinha = client.get(f"{API}/pedidos", headers=as_user("cozinha"))

    assert _ids(gerente) == {orders["c1"], orders["c2"], orders["balcao"]}
    assert _ids(gerente2) == {orders["u2"]}
    assert _ids(cozinha) == _ids(gerente)


def test_colaborador_pedindo_outra_unidade_403(
    client: TestClient, as_user: Headers, seeded: ModuleType, orders: dict[str, str]
) -> None:
    response = client.get(
        f"{API}/pedidos", params={"unidadeId": str(seeded.UNIT_2_ID)}, headers=as_user("gerente")
    )

    assert response.status_code == 403


def test_admin_ve_todos_e_filtra_por_unidade(
    client: TestClient, as_user: Headers, seeded: ModuleType, orders: dict[str, str]
) -> None:
    todos = client.get(f"{API}/pedidos", headers=as_user("admin"))
    unidade2 = client.get(
        f"{API}/pedidos", params={"unidadeId": str(seeded.UNIT_2_ID)}, headers=as_user("admin")
    )

    assert todos.json()["total"] == 4
    assert _ids(unidade2) == {orders["u2"]}


def test_filtro_canal_pedido(client: TestClient, as_user: Headers, orders: dict[str, str]) -> None:
    response = client.get(
        f"{API}/pedidos", params={"canalPedido": "BALCAO"}, headers=as_user("admin")
    )

    assert response.status_code == 200
    assert _ids(response) == {orders["balcao"]}
    assert all(o["canalPedido"] == "BALCAO" for o in response.json()["items"])


def test_filtro_status(client: TestClient, as_user: Headers, orders: dict[str, str]) -> None:
    pagos = client.get(f"{API}/pedidos", params={"status": "PAGO"}, headers=as_user("admin"))
    aguardando = client.get(
        f"{API}/pedidos", params={"status": "AGUARDANDO_PAGAMENTO"}, headers=as_user("admin")
    )

    assert pagos.json()["total"] == 0
    assert aguardando.json()["total"] == 4


def test_filtro_invalido_422(client: TestClient, as_user: Headers, orders: dict[str, str]) -> None:
    response = client.get(
        f"{API}/pedidos", params={"canalPedido": "NADA"}, headers=as_user("admin")
    )

    assert response.status_code == 422


def test_paginacao(client: TestClient, as_user: Headers, orders: dict[str, str]) -> None:
    first = client.get(f"{API}/pedidos", params={"page": 1, "limit": 3}, headers=as_user("admin"))
    second = client.get(f"{API}/pedidos", params={"page": 2, "limit": 3}, headers=as_user("admin"))

    assert first.json()["total"] == 4
    assert (first.json()["page"], first.json()["limit"]) == (1, 3)
    assert len(first.json()["items"]) == 3
    assert len(second.json()["items"]) == 1
    assert _ids(first).isdisjoint(_ids(second))


def test_obter_pedido_proprio_com_itens(
    client: TestClient, as_user: Headers, orders: dict[str, str]
) -> None:
    response = client.get(f"{API}/pedidos/{orders['c1']}", headers=as_user("cliente"))

    assert response.status_code == 200
    assert response.json()["id"] == orders["c1"]
    assert len(response.json()["itens"]) == 1


def test_pedido_de_outro_cliente_404(
    client: TestClient, as_user: Headers, orders: dict[str, str]
) -> None:
    response = client.get(f"{API}/pedidos/{orders['c1']}", headers=as_user("cliente2"))

    assert response.status_code == 404


def test_pedido_inexistente_404(client: TestClient, as_user: Headers, seeded: ModuleType) -> None:
    response = client.get(f"{API}/pedidos/{uuid4()}", headers=as_user("admin"))

    assert response.status_code == 404


def test_colaborador_de_outra_unidade_403(
    client: TestClient, as_user: Headers, orders: dict[str, str]
) -> None:
    response = client.get(f"{API}/pedidos/{orders['c1']}", headers=as_user("gerente2"))

    assert response.status_code == 403


def test_admin_e_colaborador_da_unidade_obtem(
    client: TestClient, as_user: Headers, orders: dict[str, str]
) -> None:
    assert client.get(f"{API}/pedidos/{orders['c1']}", headers=as_user("admin")).status_code == 200
    assert (
        client.get(f"{API}/pedidos/{orders['c1']}", headers=as_user("cozinha")).status_code == 200
    )  # noqa: E501


def test_listagem_sem_token_401(client: TestClient) -> None:
    assert client.get(f"{API}/pedidos").status_code == 401
