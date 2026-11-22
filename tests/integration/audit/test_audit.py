"""GET /auditoria (UC-11): ADMIN vê tudo, GERENTE só a sua unidade."""

from collections.abc import Callable
from types import ModuleType

import pytest
from fastapi.testclient import TestClient

from tests.integration.helpers import API, post_order

pytestmark = pytest.mark.integration

Headers = Callable[[str], dict[str, str]]


@pytest.fixture
def activity(client: TestClient, as_user: Headers, seeded: ModuleType) -> dict[str, str]:
    unit1 = post_order(client, as_user("cliente"), seeded).json()["id"]
    unit2 = post_order(
        client,
        as_user("gerente2"),
        seeded,
        channel="BALCAO",
        unit=seeded.UNIT_2_ID,
        items=[(seeded.PRODUCT_CUSCUZ_ID, 1)],
    ).json()["id"]
    return {"unit1": unit1, "unit2": unit2}


def test_admin_ve_toda_a_rede(
    client: TestClient, as_user: Headers, activity: dict[str, str]
) -> None:  # noqa: E501
    response = client.get(f"{API}/auditoria", headers=as_user("admin"))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {i["idRecurso"] for i in body["items"]} == set(activity.values())
    item = body["items"][0]
    assert item["acao"] == "PEDIDO_CRIADO"
    assert item["tipoRecurso"] == "PEDIDO"
    assert item["idRequisicao"]
    assert {"usuarioId", "perfil", "unidadeId", "canalPedido", "ocorridoEm", "detalhes"} <= set(
        item
    )  # noqa: E501


def test_gerente_ve_so_a_propria_unidade(
    client: TestClient, as_user: Headers, seeded: ModuleType, activity: dict[str, str]
) -> None:
    g1 = client.get(f"{API}/auditoria", headers=as_user("gerente")).json()
    g2 = client.get(f"{API}/auditoria", headers=as_user("gerente2")).json()

    assert [i["idRecurso"] for i in g1["items"]] == [activity["unit1"]]
    assert [i["idRecurso"] for i in g2["items"]] == [activity["unit2"]]
    assert g1["items"][0]["unidadeId"] == str(seeded.UNIT_1_ID)


def test_ordem_mais_recente_primeiro_e_paginacao(
    client: TestClient, as_user: Headers, activity: dict[str, str]
) -> None:
    full = client.get(f"{API}/auditoria", headers=as_user("admin")).json()["items"]
    assert [i["ocorridoEm"] for i in full] == sorted((i["ocorridoEm"] for i in full), reverse=True)

    page = client.get(
        f"{API}/auditoria", params={"page": 2, "limit": 1}, headers=as_user("admin")
    ).json()
    assert page["total"] == 2
    assert [i["id"] for i in page["items"]] == [full[1]["id"]]


def test_filtros_acao_e_tipo_recurso(
    client: TestClient, as_user: Headers, activity: dict[str, str]
) -> None:
    hit = client.get(
        f"{API}/auditoria",
        params={"acao": "PEDIDO_CRIADO", "tipoRecurso": "PEDIDO"},
        headers=as_user("admin"),
    ).json()
    miss = client.get(
        f"{API}/auditoria", params={"acao": "STATUS_ALTERADO"}, headers=as_user("admin")
    ).json()

    assert hit["total"] == 2
    assert miss == {"items": [], "page": 1, "limit": 10, "total": 0}


@pytest.mark.parametrize("user", ["cliente", "atendente", "cozinha"])
def test_outros_perfis_403(
    client: TestClient, as_user: Headers, activity: dict[str, str], user: str
) -> None:  # noqa: E501
    assert client.get(f"{API}/auditoria", headers=as_user(user)).status_code == 403


def test_sem_token_401(client: TestClient) -> None:
    assert client.get(f"{API}/auditoria").status_code == 401
