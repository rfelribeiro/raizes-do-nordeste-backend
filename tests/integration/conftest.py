"""Fixtures dos testes de integração (PostgreSQL real, banco de testes separado)."""

import functools
import importlib.util
import sys
from collections.abc import Callable, Iterator
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from uuid import UUID, uuid4

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from raizes.api.composition.payments import get_payment_gateway
from raizes.application.ports.payment_gateway import GatewayResult
from raizes.application.principal import Principal
from raizes.domain.shared.enums import PaymentAttemptStatus, PaymentMethod, Role
from raizes.infrastructure.config import get_settings
from raizes.infrastructure.db.session import get_engine
from raizes.infrastructure.security.jwt_service import JwtTokenService
from raizes.main import create_app

# Trava de segurança: a limpeza entre testes apaga TODAS as tabelas, então os testes só rodam num
# banco de testes (`make test-integration` cria `<POSTGRES_DB>_teste`) ou no banco efêmero da CI.


@pytest.fixture(scope="session", autouse=True)
def _only_test_database() -> None:
    settings = get_settings()
    if not (settings.postgres_db.endswith("_teste") or settings.app_env == "ci"):
        pytest.exit(
            "Testes de integração só rodam num banco de testes (nome terminando em _teste). "
            "Use `make test-integration`.",
            returncode=2,
        )


class FakeGateway:
    """Gateway de pagamento determinístico: o token decide o resultado (como no mock real)."""

    def __init__(self) -> None:
        self.calls: list[tuple[UUID, Decimal, PaymentMethod, str]] = []
        self.on_charge: Callable[[UUID], None] | None = None

    def charge(
        self, order_id: UUID, amount: Decimal, method: PaymentMethod, token: str
    ) -> GatewayResult:
        self.calls.append((order_id, amount, method, token))
        if self.on_charge is not None:
            self.on_charge(order_id)
        if token == "tok_recusado":
            return GatewayResult(
                status=PaymentAttemptStatus.RECUSADO, refusal_reason="Saldo insuficiente"
            )
        if token == "tok_timeout":
            return GatewayResult(status=PaymentAttemptStatus.FALHA, calls=3)
        return GatewayResult(status=PaymentAttemptStatus.APROVADO, transaction_id="tx_fake_001")


@pytest.fixture
def fake_gateway() -> FakeGateway:
    return FakeGateway()


@pytest.fixture
def client(fake_gateway: FakeGateway) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_payment_gateway] = lambda: fake_gateway
    with TestClient(app) as test_client:
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


@pytest.fixture(scope="session")
def seed_module() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / "seed.py"
    spec = importlib.util.spec_from_file_location("seed_fixture", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["seed_fixture"] = module
    spec.loader.exec_module(module)
    # Hash barato: os testes geram os tokens direto, sem passar pelo login.
    module.PasswordHasher = functools.partial(
        PasswordHasher, time_cost=1, memory_cost=8, parallelism=1
    )
    return module


@pytest.fixture
def seeded(seed_module: ModuleType) -> ModuleType:
    """Carga inicial de demonstração (UUIDs fixos) gravada no banco de testes."""
    with Session(get_engine()) as session:
        seed_module.seed(session)
    return seed_module


@pytest.fixture
def as_user(
    seeded: ModuleType, auth_headers: Callable[..., dict[str, str]]
) -> Callable[[str], dict[str, str]]:
    """Cabeçalhos de um usuário da carga inicial: cliente, cliente2, atendente, cozinha,
    gerente, gerente2 ou admin."""
    table: dict[str, tuple[Role, UUID | None, UUID]] = {
        "cliente": (Role.CLIENTE, None, seeded.CLIENT_1_ID),
        "cliente2": (Role.CLIENTE, None, seeded.CLIENT_2_ID),
        "atendente": (Role.ATENDENTE, seeded.UNIT_1_ID, seeded.ATTENDANT_ID),
        "cozinha": (Role.COZINHA, seeded.UNIT_1_ID, seeded.KITCHEN_ID),
        "gerente": (Role.GERENTE, seeded.UNIT_1_ID, seeded.MANAGER_1_ID),
        "gerente2": (Role.GERENTE, seeded.UNIT_2_ID, seeded.MANAGER_2_ID),
        "admin": (Role.ADMIN, None, seeded.ADMIN_ID),
    }

    def build(name: str) -> dict[str, str]:
        role, unit_id, user_id = table[name]
        return auth_headers(role, unit_id=unit_id, user_id=user_id)

    return build
