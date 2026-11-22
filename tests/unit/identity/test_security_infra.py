"""Hasher Argon2id e serviço JWT (sem banco)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from raizes.application.errors import AuthenticationError
from raizes.application.principal import Principal
from raizes.domain.shared.enums import Role
from raizes.infrastructure.security.jwt_service import ALGORITHM, ISSUER, JwtTokenService
from raizes.infrastructure.security.password import Argon2PasswordHasher

CHAVE = "chave-ficticia-de-teste-com-tamanho-suficiente-0123456789"


def test_hasher_gera_argon2id_e_verifica() -> None:
    hasher = Argon2PasswordHasher()
    hashed = hasher.hash("Senha@Ficticia1")
    assert hashed.startswith("$argon2id$")
    assert hasher.verify("Senha@Ficticia1", hashed)
    assert not hasher.verify("outra", hashed)


def test_hasher_hash_invalido_nao_levanta() -> None:
    assert not Argon2PasswordHasher().verify("x", "isto-nao-e-um-hash")


def test_hasher_usa_sal_diferente_a_cada_hash() -> None:
    hasher = Argon2PasswordHasher()
    assert hasher.hash("mesma") != hasher.hash("mesma")


def test_jwt_ida_e_volta_com_claims() -> None:
    service = JwtTokenService(CHAVE, 60)
    principal = Principal(uuid4(), Role.GERENTE, uuid4())
    issued = service.issue(principal)
    assert issued.expires_in == 3600
    claims = jwt.decode(issued.access_token, CHAVE, algorithms=[ALGORITHM], issuer=ISSUER)
    assert {"sub", "perfil", "unidade", "iat", "exp", "iss"} <= set(claims)
    assert claims["perfil"] == "GERENTE"
    assert service.decode(issued.access_token) == principal


def test_jwt_sem_unidade() -> None:
    service = JwtTokenService(CHAVE)
    principal = Principal(uuid4(), Role.CLIENTE, None)
    assert service.decode(service.issue(principal).access_token) == principal


def _token(claims: dict[str, object], key: str = CHAVE) -> str:
    return jwt.encode(claims, key, algorithm=ALGORITHM)


def _claims_validos() -> dict[str, object]:
    now = datetime.now(UTC)
    return {
        "sub": str(uuid4()),
        "perfil": "CLIENTE",
        "unidade": None,
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "iss": ISSUER,
    }


def test_jwt_expirado() -> None:
    claims = _claims_validos()
    claims["exp"] = datetime.now(UTC) - timedelta(seconds=10)
    with pytest.raises(AuthenticationError):
        JwtTokenService(CHAVE).decode(_token(claims))


def test_jwt_assinatura_errada() -> None:
    with pytest.raises(AuthenticationError):
        JwtTokenService(CHAVE).decode(_token(_claims_validos(), key="outra-chave" * 4))


@pytest.mark.parametrize("faltando", ["sub", "perfil", "iat", "exp", "iss"])
def test_jwt_claim_ausente(faltando: str) -> None:
    claims = _claims_validos()
    del claims[faltando]
    with pytest.raises(AuthenticationError):
        JwtTokenService(CHAVE).decode(_token(claims))


def test_jwt_lixo_e_perfil_desconhecido() -> None:
    service = JwtTokenService(CHAVE)
    with pytest.raises(AuthenticationError):
        service.decode("nao.e.jwt")
    claims = _claims_validos()
    claims["perfil"] = "SUPERUSUARIO"
    with pytest.raises(AuthenticationError):
        service.decode(_token(claims))
