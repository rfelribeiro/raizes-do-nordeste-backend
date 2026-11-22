"""Composição do módulo de identidade."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from raizes.api.composition.db import get_session
from raizes.application.identity.login import Login
from raizes.application.ports.security import PasswordHasher, TokenService
from raizes.infrastructure.config import get_settings
from raizes.infrastructure.db.repositories.identity import SqlAlchemyUserRepository
from raizes.infrastructure.security.jwt_service import JwtTokenService
from raizes.infrastructure.security.password import Argon2PasswordHasher


@lru_cache
def get_password_hasher() -> PasswordHasher:
    return Argon2PasswordHasher()


@lru_cache
def get_token_service() -> TokenService:
    settings = get_settings()
    return JwtTokenService(settings.jwt_secret.get_secret_value(), settings.jwt_expires_minutes)


@lru_cache
def _dummy_hash() -> str:
    return get_password_hasher().hash("senha-ficticia-para-igualar-tempo")


def get_login(
    session: Annotated[Session, Depends(get_session)],
    hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
    tokens: Annotated[TokenService, Depends(get_token_service)],
) -> Login:
    return Login(SqlAlchemyUserRepository(session), hasher, tokens, _dummy_hash())
