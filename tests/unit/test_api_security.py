"""get_principal, require_roles, paginação e novos erros de aplicação (sem banco)."""

from typing import Annotated
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from raizes.api.composition.identity import get_token_service
from raizes.api.pagination import Page, PageParams, PageQuery
from raizes.api.security import get_principal, require_roles
from raizes.application.errors import (
    ApplicationValidationError,
    AuthenticationError,
    ConflictError,
    DependencyTimeoutError,
    PermissionDeniedError,
)
from raizes.application.ports.security import IssuedToken
from raizes.application.principal import Principal
from raizes.domain.shared.enums import Role
from raizes.main import create_app

GERENTE = Principal(uuid4(), Role.GERENTE, uuid4())


class FakeTokens:
    def issue(self, principal: Principal) -> IssuedToken:  # pragma: no cover
        raise NotImplementedError

    def decode(self, token: str) -> Principal:
        if token == "valido":
            return GERENTE
        raise AuthenticationError("Token inválido ou expirado.")


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_token_service] = lambda: FakeTokens()

    @app.get("/_eu")
    def eu(principal: Annotated[Principal, Depends(get_principal)]) -> dict[str, str]:
        return {"perfil": principal.role.value}

    @app.get("/_so-admin")
    def so_admin(
        principal: Annotated[Principal, Depends(require_roles(Role.ADMIN))],
    ) -> dict[str, str]:
        return {"perfil": principal.role.value}

    @app.get("/_gerente-ou-admin")
    def gerente(
        principal: Annotated[Principal, Depends(require_roles(Role.GERENTE, Role.ADMIN))],
    ) -> dict[str, str]:
        return {"perfil": principal.role.value}

    @app.get("/_pagina")
    def pagina(params: PageQuery) -> Page[int]:
        return Page[int](items=[], page=params.page, limit=params.limit, total=0)

    return TestClient(app)


def test_sem_token_401(client: TestClient) -> None:
    response = client.get("/_eu")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"] == "NAO_AUTENTICADO"


def test_esquema_nao_bearer_401(client: TestClient) -> None:
    assert client.get("/_eu", headers={"Authorization": "Basic abc"}).status_code == 401


def test_token_invalido_401(client: TestClient) -> None:
    response = client.get("/_eu", headers={"Authorization": "Bearer lixo"})
    assert response.status_code == 401
    assert response.json()["error"] == "NAO_AUTENTICADO"


def test_token_valido_200(client: TestClient) -> None:
    response = client.get("/_eu", headers={"Authorization": "Bearer valido"})
    assert response.status_code == 200
    assert response.json() == {"perfil": "GERENTE"}


def test_perfil_errado_403(client: TestClient) -> None:
    response = client.get("/_so-admin", headers={"Authorization": "Bearer valido"})
    assert response.status_code == 403
    assert response.json()["error"] == "SEM_PERMISSAO"


def test_perfil_permitido_200(client: TestClient) -> None:
    response = client.get("/_gerente-ou-admin", headers={"Authorization": "Bearer valido"})
    assert response.status_code == 200


def test_require_roles_sem_token_401(client: TestClient) -> None:
    assert client.get("/_so-admin").status_code == 401


def test_swagger_tem_esquema_bearer(client: TestClient) -> None:
    schemes = client.get("/openapi.json").json()["components"]["securitySchemes"]
    assert any(s["type"] == "http" and s["scheme"] == "bearer" for s in schemes.values())


def test_paginacao_padrao_e_limites(client: TestClient) -> None:
    assert client.get("/_pagina").json() == {"items": [], "page": 1, "limit": 10, "total": 0}
    assert client.get("/_pagina?page=2&limit=100").status_code == 200
    for query in ("page=0", "limit=0", "limit=101", "page=x"):
        response = client.get(f"/_pagina?{query}")
        assert response.status_code == 422, query
        assert response.json()["error"] == "VALIDACAO_FALHOU"


def test_page_params_offset() -> None:
    assert PageParams(page=3, limit=10).offset == 20


@pytest.mark.parametrize(
    ("error", "status", "codigo"),
    [
        (AuthenticationError("x"), 401, "NAO_AUTENTICADO"),
        (PermissionDeniedError("x"), 403, "SEM_PERMISSAO"),
        (ConflictError("x"), 409, "CONFLITO"),
        (
            ApplicationValidationError("x", detalhes=[{"field": "a", "issue": "b"}]),
            422,
            "VALIDACAO_FALHOU",
        ),
        (DependencyTimeoutError("x"), 504, "TEMPO_ESGOTADO"),
    ],
)
def test_erros_de_aplicacao_mapeados(error: Exception, status: int, codigo: str) -> None:
    app: FastAPI = create_app()

    @app.get("/_boom")
    def boom() -> None:
        raise error

    response = TestClient(app).get("/_boom")
    assert response.status_code == status
    body = response.json()
    assert body["error"] == codigo
    assert ("www-authenticate" in response.headers) == (status == 401)
    if status == 422:
        assert body["details"] == [{"field": "a", "issue": "b"}]
