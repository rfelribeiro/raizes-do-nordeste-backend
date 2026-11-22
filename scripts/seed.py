"""Carga inicial (dados fictícios de demonstração). Idempotente: pode rodar várias vezes.

Uso: `make seed`. Os UUIDs são FIXOS (a coleção Postman os referencia). A senha de demonstração
é fictícia e só para uso local; este script nunca a imprime, nem os hashes.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from argon2 import PasswordHasher
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from raizes.domain.shared.enums import (
    ConsentAction,
    ConsentPurpose,
    Role,
    StockMovementType,
    UnitFormat,
)
from raizes.infrastructure.db.models import (
    Category,
    Consent,
    MenuItem,
    Product,
    Stock,
    StockMovement,
    Unit,
    User,
)
from raizes.infrastructure.db.session import get_engine

DEMO_PASSWORD = "Demo@2026"  # segredos:permitir (fictícia, só uso local; ver README)


def _id(n: int) -> uuid.UUID:
    return uuid.UUID(f"00000000-0000-4000-8000-{n:012d}")


# --- UUIDs fixos -----------------------------------------------------------------------------
UNIT_1_ID = _id(101)  # COMPLETA
UNIT_2_ID = _id(102)  # REDUZIDA

CATEGORY_SALGADOS_ID = _id(201)
CATEGORY_BEBIDAS_ID = _id(202)
CATEGORY_JUNINOS_ID = _id(203)

PRODUCT_TAPIOCA_ID = _id(301)
PRODUCT_CUSCUZ_ID = _id(302)
PRODUCT_BAIAO_ID = _id(303)
PRODUCT_CARNE_SOL_ID = _id(304)  # estoque 2 na unidade 1 (teste de 409)
PRODUCT_SUCO_CAJU_ID = _id(305)
PRODUCT_CANJICA_ID = _id(306)  # sazonal

CLIENT_1_ID = _id(401)
CLIENT_2_ID = _id(402)
ATTENDANT_ID = _id(403)
KITCHEN_ID = _id(404)
MANAGER_1_ID = _id(405)
MANAGER_2_ID = _id(406)
ADMIN_ID = _id(407)

CONSENT_CLIENT_1_FIDELITY_ID = _id(501)
LOW_STOCK_MOVEMENT_ID = _id(601)

SEASON_START = date(2026, 6, 1)
SEASON_END = date(2026, 7, 31)


@dataclass(frozen=True)
class _U:
    id: uuid.UUID
    name: str
    email: str
    role: Role
    unit_id: uuid.UUID | None


USERS = (
    _U(CLIENT_1_ID, "Maria das Dores (demo)", "cliente@exemplo.com", Role.CLIENTE, None),
    _U(CLIENT_2_ID, "José Bezerra (demo)", "cliente2@exemplo.com", Role.CLIENTE, None),
    _U(ATTENDANT_ID, "Ana Atendente (demo)", "atendente@exemplo.com", Role.ATENDENTE, UNIT_1_ID),
    _U(KITCHEN_ID, "Carlos Cozinha (demo)", "cozinha@exemplo.com", Role.COZINHA, UNIT_1_ID),
    _U(MANAGER_1_ID, "Gabriela Gerente (demo)", "gerente@exemplo.com", Role.GERENTE, UNIT_1_ID),
    _U(MANAGER_2_ID, "Geraldo Gerente (demo)", "gerente2@exemplo.com", Role.GERENTE, UNIT_2_ID),
    _U(ADMIN_ID, "Admin da Rede (demo)", "admin@exemplo.com", Role.ADMIN, None),
)

# (id, nome, descricao, categoria, preço de referência, sazonal)
PRODUCTS = (
    (
        PRODUCT_TAPIOCA_ID,
        "Tapioca de queijo coalho",
        "Tapioca recheada com queijo coalho",
        CATEGORY_SALGADOS_ID,
        "12.00",
        False,
    ),
    (
        PRODUCT_CUSCUZ_ID,
        "Cuscuz com ovo",
        "Cuscuz nordestino com ovo mexido",
        CATEGORY_SALGADOS_ID,
        "10.50",
        False,
    ),
    (
        PRODUCT_BAIAO_ID,
        "Baião de dois",
        "Arroz, feijão-de-corda e queijo coalho",
        CATEGORY_SALGADOS_ID,
        "28.00",
        False,
    ),
    (
        PRODUCT_CARNE_SOL_ID,
        "Carne de sol com macaxeira",
        "Carne de sol acebolada com macaxeira",
        CATEGORY_SALGADOS_ID,
        "39.90",
        False,
    ),
    (
        PRODUCT_SUCO_CAJU_ID,
        "Suco de caju",
        "Suco natural de caju (400 ml)",
        CATEGORY_BEBIDAS_ID,
        "8.00",
        False,
    ),
    (
        PRODUCT_CANJICA_ID,
        "Canjica",
        "Canjica cremosa de milho (festas juninas)",
        CATEGORY_JUNINOS_ID,
        "9.00",
        True,
    ),
)

# Cardápio: (unidade, produto, preço local, sazonal?). A unidade REDUZIDA não oferta carne de sol.
MENU = (
    (UNIT_1_ID, PRODUCT_TAPIOCA_ID, None, False),
    (UNIT_1_ID, PRODUCT_CUSCUZ_ID, "11.00", False),
    (UNIT_1_ID, PRODUCT_BAIAO_ID, None, False),
    (UNIT_1_ID, PRODUCT_CARNE_SOL_ID, None, False),
    (UNIT_1_ID, PRODUCT_SUCO_CAJU_ID, None, False),
    (UNIT_1_ID, PRODUCT_CANJICA_ID, None, True),
    (UNIT_2_ID, PRODUCT_TAPIOCA_ID, "12.50", False),
    (UNIT_2_ID, PRODUCT_CUSCUZ_ID, None, False),
    (UNIT_2_ID, PRODUCT_SUCO_CAJU_ID, None, False),
    (UNIT_2_ID, PRODUCT_CANJICA_ID, None, True),
)

LOW_STOCK = 2
COMFORTABLE_STOCK = 500


def _upsert_nothing(session: Session, model: type, values: dict[str, object]) -> None:
    """INSERT ... ON CONFLICT DO NOTHING (usa a PK/uniques do modelo)."""
    session.execute(insert(model).values(**values).on_conflict_do_nothing())


def seed(session: Session) -> dict[str, int]:
    hasher = PasswordHasher()  # Argon2id por padrão

    for uid, code, name, city, fmt in (
        (UNIT_1_ID, "REC-01", "Raízes Boa Viagem (demo)", "Recife", UnitFormat.COMPLETA),
        (UNIT_2_ID, "FOR-01", "Raízes Beira-Mar (demo)", "Fortaleza", UnitFormat.REDUZIDA),
    ):
        state = "PE" if code.startswith("REC") else "CE"
        _upsert_nothing(
            session,
            Unit,
            {"id": uid, "code": code, "name": name, "city": city, "state": state, "format": fmt},
        )

    for cid, name in (
        (CATEGORY_SALGADOS_ID, "Salgados"),
        (CATEGORY_BEBIDAS_ID, "Bebidas"),
        (CATEGORY_JUNINOS_ID, "Juninos"),
    ):
        _upsert_nothing(session, Category, {"id": cid, "name": name})

    for pid, name, desc, cat, price, seasonal in PRODUCTS:
        _upsert_nothing(
            session,
            Product,
            {
                "id": pid,
                "name": name,
                "description": desc,
                "category_id": cat,
                "reference_price": Decimal(price),
                "is_seasonal": seasonal,
            },
        )

    for unit_id, product_id, price, seasonal in MENU:
        _upsert_nothing(
            session,
            MenuItem,
            {
                "id": uuid.uuid5(unit_id, str(product_id)),
                "unit_id": unit_id,
                "product_id": product_id,
                "local_price": Decimal(price) if price else None,
                "season_start": SEASON_START if seasonal else None,
                "season_end": SEASON_END if seasonal else None,
            },
        )
        is_low = (unit_id, product_id) == (UNIT_1_ID, PRODUCT_CARNE_SOL_ID)
        qty = LOW_STOCK if is_low else COMFORTABLE_STOCK
        _upsert_nothing(
            session,
            Stock,
            {"unit_id": unit_id, "product_id": product_id, "available_qty": qty, "reserved_qty": 0},
        )

    # Razão: a entrada inicial do produto de estoque baixo (o saldo é explicado pelo razão).
    _upsert_nothing(
        session,
        StockMovement,
        {
            "id": LOW_STOCK_MOVEMENT_ID,
            "unit_id": UNIT_1_ID,
            "product_id": PRODUCT_CARNE_SOL_ID,
            "type": StockMovementType.ENTRADA,
            "moved_qty": LOW_STOCK,
            "reason": "Carga inicial de demonstração",
        },
    )

    # Só gera o hash (caro) se o usuário ainda não existir.
    existing = set(session.scalars(select(User.id)))
    for u in USERS:
        if u.id in existing:
            continue
        _upsert_nothing(
            session,
            User,
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "password_hash": hasher.hash(DEMO_PASSWORD),
                "role": u.role,
                "unit_id": u.unit_id,
            },
        )

    _upsert_nothing(
        session,
        Consent,
        {
            "id": CONSENT_CLIENT_1_FIDELITY_ID,
            "user_id": CLIENT_1_ID,
            "purpose": ConsentPurpose.FIDELIDADE,
            "action": ConsentAction.CONCEDIDO,
            "legal_basis": "CONSENTIMENTO_ART_7_I",
            "terms_version": "v1",
        },
    )
    session.commit()

    return {
        "unidades": session.scalar(select(func.count()).select_from(Unit)) or 0,
        "usuarios": session.scalar(select(func.count()).select_from(User)) or 0,
        "categorias": session.scalar(select(func.count()).select_from(Category)) or 0,
        "produtos": session.scalar(select(func.count()).select_from(Product)) or 0,
        "itens_cardapio": session.scalar(select(func.count()).select_from(MenuItem)) or 0,
        "estoques": session.scalar(select(func.count()).select_from(Stock)) or 0,
        "movimentacoes_estoque": session.scalar(select(func.count()).select_from(StockMovement))
        or 0,
        "consentimentos": session.scalar(select(func.count()).select_from(Consent)) or 0,
    }


def main() -> None:
    with Session(get_engine()) as session:
        counts = seed(session)
    for table, total in counts.items():
        print(f"{table}: {total}")


if __name__ == "__main__":
    main()
