"""Esquema do MVP no PostgreSQL real: migração, carga inicial e restrições do banco."""

import importlib.util
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Connection, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from raizes.infrastructure.db.session import get_engine

pytestmark = pytest.mark.integration

TABELAS_MVP = {
    "unidades",
    "usuarios",
    "categorias",
    "produtos",
    "itens_cardapio",
    "estoques",
    "movimentacoes_estoque",
    "pedidos",
    "itens_pedido",
    "historico_status_pedido",
    "tentativas_pagamento",
    "consentimentos",
    "auditoria",
    "outbox_eventos",
}


def _load_seed() -> Any:
    path = Path(__file__).resolve().parents[3] / "scripts" / "seed.py"
    spec = importlib.util.spec_from_file_location("seed_script", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["seed_script"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def conn() -> Iterator[Connection]:
    """Conexão dentro de uma transação que nunca é confirmada (nada fica gravado)."""
    with get_engine().connect() as connection, connection.begin() as tx:
        yield connection
        tx.rollback()


def _unit(conn: Connection) -> uuid.UUID:
    uid = uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO unidades (id, codigo, nome, cidade, uf, formato) "
            "VALUES (:id, :cod, 'U', 'Recife', 'PE', 'COMPLETA')"
        ),
        {"id": uid, "cod": uid.hex[:20]},
    )
    return uid


def _user(conn: Connection, email: str) -> uuid.UUID:
    uid = uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO usuarios (id, nome, email, senha_hash, perfil) "
            "VALUES (:id, 'N', :email, 'x', 'CLIENTE')"
        ),
        {"id": uid, "email": email},
    )
    return uid


def _product(conn: Connection) -> uuid.UUID:
    cat, prod = uuid.uuid4(), uuid.uuid4()
    conn.execute(
        text("INSERT INTO categorias (id, nome) VALUES (:id, :n)"),
        {"id": cat, "n": cat.hex},
    )
    conn.execute(
        text(
            "INSERT INTO produtos (id, id_categoria, nome, valor_preco_referencia) "
            "VALUES (:id, :cat, 'P', 10.00)"
        ),
        {"id": prod, "cat": cat},
    )
    return prod


def _order(conn: Connection, unit: uuid.UUID, user: uuid.UUID, canal: str = "APP") -> uuid.UUID:
    oid = uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO pedidos (id, id_unidade, id_usuario_criador, canal_pedido, status, "
            "valor_itens, valor_total, expira_em) "
            "VALUES (:id, :u, :c, :canal, 'AGUARDANDO_PAGAMENTO', 10, 10, now())"
        ),
        {"id": oid, "u": unit, "c": user, "canal": canal},
    )
    return oid


def test_migration_created_mvp_tables() -> None:
    assert set(inspect(get_engine()).get_table_names()) >= TABELAS_MVP


def test_seed_runs_twice_with_same_counts() -> None:
    seed = _load_seed()
    with Session(get_engine()) as session:
        first = seed.seed(session)
    with Session(get_engine()) as session:
        second = seed.seed(session)
    assert first == second
    assert first["unidades"] >= 2
    assert first["usuarios"] >= 7
    assert first["produtos"] >= 6


def test_database_rejects_negative_stock(conn: Connection) -> None:
    unit, product = _unit(conn), _product(conn)
    with pytest.raises(IntegrityError, match="ck_estoques_qtd_disponivel"):
        conn.execute(
            text(
                "INSERT INTO estoques (id_unidade, id_produto, qtd_disponivel, qtd_reservada) "
                "VALUES (:u, :p, -1, 0)"
            ),
            {"u": unit, "p": product},
        )


def test_database_rejects_duplicate_email_ignoring_case(conn: Connection) -> None:
    _user(conn, "Dup@exemplo.com")
    with pytest.raises(IntegrityError, match="uq_usuarios_email_lower"):
        _user(conn, "dup@EXEMPLO.com")


def test_database_rejects_invalid_order_channel(conn: Connection) -> None:
    unit, user = _unit(conn), _user(conn, "c1@exemplo.com")
    with pytest.raises(IntegrityError, match="ck_pedidos_canal_pedido"):
        _order(conn, unit, user, canal="FAX")


def test_database_rejects_incoherent_item_total(conn: Connection) -> None:
    unit, user = _unit(conn), _user(conn, "c2@exemplo.com")
    product = _product(conn)
    order = _order(conn, unit, user)
    with pytest.raises(IntegrityError, match="ck_itens_pedido_valor_total_item"):
        conn.execute(
            text(
                "INSERT INTO itens_pedido (id, id_pedido, id_produto, qtd_item, "
                "valor_preco_unitario, valor_total_item) VALUES (:id, :o, :p, 2, 10.00, 25.00)"
            ),
            {"id": uuid.uuid4(), "o": order, "p": product},
        )
