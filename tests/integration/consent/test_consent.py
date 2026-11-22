"""POST e GET /consentimentos (UC-09, LGPD): histórico append-only e vigente por finalidade."""

from collections.abc import Callable
from types import ModuleType

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from tests.integration.helpers import API, scalar

pytestmark = pytest.mark.integration

Headers = Callable[[str], dict[str, str]]


def _register(
    client: TestClient, headers: dict[str, str], purpose: str, action: str, version: str = "v1"
) -> Response:
    return client.post(
        f"{API}/consentimentos",
        json={"finalidade": purpose, "acao": action, "versaoTermo": version},
        headers=headers,
    )


def test_conceder_revogar_e_vigente(
    client: TestClient, as_user: Headers, seeded: ModuleType
) -> None:
    headers = as_user("cliente2")  # sem consentimentos na carga inicial

    granted = _register(client, headers, "MARKETING", "CONCEDIDO")
    assert granted.status_code == 201
    assert granted.json()["acao"] == "CONCEDIDO"
    assert granted.json()["baseLegal"]

    listing = client.get(f"{API}/consentimentos", headers=headers).json()
    assert [c["acao"] for c in listing["vigentes"]] == ["CONCEDIDO"]

    revoked = _register(client, headers, "MARKETING", "REVOGADO", "v2")
    assert revoked.status_code == 201

    listing = client.get(f"{API}/consentimentos", headers=headers).json()
    assert [c["acao"] for c in listing["historico"]] == ["CONCEDIDO", "REVOGADO"]  # nada é apagado
    assert [(c["finalidade"], c["acao"], c["versaoTermo"]) for c in listing["vigentes"]] == [
        ("MARKETING", "REVOGADO", "v2")
    ]
    assert scalar("SELECT count(*) FROM auditoria WHERE acao = 'CONSENTIMENTO_REGISTRADO'") == 2


def test_lista_traz_so_os_proprios(
    client: TestClient, as_user: Headers, seeded: ModuleType
) -> None:
    # A carga inicial dá ao cliente 1 a FIDELIDADE concedida; o cliente 2 não vê nada.
    own = client.get(f"{API}/consentimentos", headers=as_user("cliente")).json()
    other = client.get(f"{API}/consentimentos", headers=as_user("cliente2")).json()

    assert [c["finalidade"] for c in own["vigentes"]] == ["FIDELIDADE"]
    assert other == {"historico": [], "vigentes": []}


def test_conceder_duas_vezes_409(client: TestClient, as_user: Headers, seeded: ModuleType) -> None:
    response = _register(client, as_user("cliente"), "FIDELIDADE", "CONCEDIDO")

    assert response.status_code == 409


def test_revogar_sem_vigente_409(client: TestClient, as_user: Headers, seeded: ModuleType) -> None:
    response = _register(client, as_user("cliente2"), "MARKETING", "REVOGADO")

    assert response.status_code == 409


def test_corpo_invalido_422(client: TestClient, as_user: Headers, seeded: ModuleType) -> None:
    assert _register(client, as_user("cliente"), "OUTRA", "CONCEDIDO").status_code == 422
    assert _register(client, as_user("cliente"), "MARKETING", "CONCEDIDO", "").status_code == 422


def test_colaborador_403(client: TestClient, as_user: Headers, seeded: ModuleType) -> None:
    assert _register(client, as_user("atendente"), "MARKETING", "CONCEDIDO").status_code == 403
    assert client.get(f"{API}/consentimentos", headers=as_user("admin")).status_code == 403


def test_sem_token_401(client: TestClient) -> None:
    assert client.get(f"{API}/consentimentos").status_code == 401
