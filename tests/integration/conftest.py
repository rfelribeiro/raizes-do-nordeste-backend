"""Fixtures dos testes de integração (PostgreSQL real do compose)."""

from collections.abc import Callable, Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from raizes.application.principal import Principal
from raizes.domain.shared.enums import Role
from raizes.infrastructure.config import get_settings
from raizes.infrastructure.db.session import get_engine
from raizes.infrastructure.security.jwt_service import JwtTokenService
from raizes.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_tables() -> Iterator[None]:
    """Esvazia as tabelas de negócio (schema public, exceto alembic_version) após cada teste."""
    yield
    with get_engine().begin() as connection:
        tables = (
            connection.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
                )
            )
            .scalars()
            .all()
        )
        if tables:
            names = ", ".join(f'public."{name}"' for name in tables)
            connection.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def auth_headers() -> Callable[..., dict[str, str]]:
    """Fábrica de cabeçalhos `Authorization` com um token real, emitido pelo JwtTokenService."""
    settings = get_settings()
    service = JwtTokenService(settings.jwt_secret.get_secret_value(), settings.jwt_expires_minutes)

    def build(
        role: Role, unit_id: UUID | None = None, user_id: UUID | None = None
    ) -> dict[str, str]:
        principal = Principal(user_id=user_id or uuid4(), role=role, unit_id=unit_id)
        return {"Authorization": f"Bearer {service.issue(principal).access_token}"}

    return build
