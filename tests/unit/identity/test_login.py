"""Caso de uso Login com fakes, e POST /auth/login via TestClient com repositório falso."""

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from raizes.api.composition.db import get_session
from raizes.api.composition.identity import get_login
from raizes.application.errors import AuthenticationError
from raizes.application.identity.credentials import UserCredentials
from raizes.application.identity.login import MENSAGEM_CREDENCIAIS_INVALIDAS, Login
from raizes.application.ports.security import IssuedToken
from raizes.application.principal import Principal
from raizes.domain.shared.enums import Role
from raizes.main import create_app


class FakeHasher:
    def __init__(self) -> None:
        self.verified: list[str] = []

    def hash(self, password: str) -> str:
        return f"hash:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        self.verified.append(password_hash)
        return password_hash == f"hash:{password}"


class FakeTokens:
    def issue(self, principal: Principal) -> IssuedToken:
        return IssuedToken(access_token=f"tok-{principal.role}", expires_in=3600)

    def decode(self, token: str) -> Principal:  # pragma: no cover - não usado aqui
        raise NotImplementedError


class FakeUsers:
    def __init__(self, *users: tuple[str, UserCredentials]) -> None:
        self._by_email = {email.lower(): cred for email, cred in users}

    def get_credentials_by_email(self, email: str) -> UserCredentials | None:
        return self._by_email.get(email.lower())


def _cred(password: str = "certa", active: bool = True) -> UserCredentials:
    return UserCredentials(uuid4(), Role.ATENDENTE, uuid4(), f"hash:{password}", active)


def _login(users: FakeUsers, hasher: FakeHasher | None = None) -> Login:
    return Login(users, hasher or FakeHasher(), FakeTokens())


def test_login_ok() -> None:
    issued = _login(FakeUsers(("a@x.com", _cred()))).execute("A@X.com", "certa")
    assert issued == IssuedToken("tok-ATENDENTE", 3600)


@pytest.mark.parametrize("cenario", ["inexistente", "inativo", "senha_errada"])
def test_login_falha_com_mesma_mensagem(cenario: str) -> None:
    users = FakeUsers(("inativo@x.com", _cred(active=False)), ("ok@x.com", _cred()))
    email, senha = {
        "inexistente": ("nao@x.com", "certa"),
        "inativo": ("inativo@x.com", "certa"),
        "senha_errada": ("ok@x.com", "errada"),
    }[cenario]
    with pytest.raises(AuthenticationError) as info:
        _login(users).execute(email, senha)
    assert info.value.message == MENSAGEM_CREDENCIAIS_INVALIDAS
    assert info.value.codigo == "NAO_AUTENTICADO"


def test_login_usuario_inexistente_verifica_hash_ficticio() -> None:
    hasher = FakeHasher()
    login = _login(FakeUsers(), hasher)
    with pytest.raises(AuthenticationError):
        login.execute("nao@x.com", "qualquer")
    assert hasher.verified == ["hash:senha-ficticia-para-igualar-tempo"]


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_login] = lambda: _login(FakeUsers(("a@x.com", _cred())))
    app.dependency_overrides[get_session] = lambda: None
    yield TestClient(app)


def test_endpoint_login_200_camel_case(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"email": "a@x.com", "senha": "certa"})
    assert response.status_code == 200
    assert response.json() == {
        "accessToken": "tok-ATENDENTE",
        "tokenType": "bearer",
        "expiresIn": 3600,
    }


def test_endpoint_login_401_padrao(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"email": "a@x.com", "senha": "errada"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    body = response.json()
    assert body["error"] == "NAO_AUTENTICADO"
    assert body["message"] == MENSAGEM_CREDENCIAIS_INVALIDAS


def test_endpoint_login_422(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"email": "a@x.com"})
    assert response.status_code == 422
    assert response.json()["details"][0]["field"] == "senha"


def test_login_documentado_no_swagger(client: TestClient) -> None:
    assert "/api/v1/auth/login" in client.get("/openapi.json").json()["paths"]
