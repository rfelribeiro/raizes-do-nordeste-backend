from dataclasses import dataclass
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from raizes.domain.shared.events import DomainEvent
from raizes.infrastructure.db.models.outbox import OutboxEvento
from raizes.infrastructure.db.outbox import SqlAlchemyOutboxWriter
from raizes.infrastructure.db.session import get_engine

pytestmark = pytest.mark.integration


@dataclass(frozen=True, kw_only=True)
class EventoDeTeste(DomainEvent):
    valor: int = 0

    def payload(self) -> dict[str, Any]:
        return {"valor": self.valor}


def _evento(valor: int = 1) -> EventoDeTeste:
    return EventoDeTeste(aggregate_type="teste", aggregate_id="a-1", valor=valor)


def test_grava_e_le_evento_na_mesma_transacao() -> None:
    evento = _evento(5)
    # A transação externa nunca é confirmada: nada fica gravado no banco após o teste.
    with get_engine().connect() as connection, connection.begin() as transaction:
        with Session(bind=connection) as session:
            SqlAlchemyOutboxWriter(session).add([evento])
            session.flush()
            linha = session.scalars(
                select(OutboxEvento).where(OutboxEvento.id_evento == evento.event_id)
            ).one()
            assert linha.tipo_evento == "evento_de_teste"
            assert linha.payload == {"valor": 5}
            assert linha.versao_schema == 1
            assert linha.ocorrido_em == evento.occurred_at
            assert linha.registrado_em is not None
            assert linha.id_sequencial > 0
        transaction.rollback()


def test_rollback_descarta_o_evento() -> None:
    evento = _evento()
    with get_engine().connect() as connection:
        with Session(bind=connection) as session:
            SqlAlchemyOutboxWriter(session).add([evento])
            session.flush()
            session.rollback()
        total = connection.execute(
            select(OutboxEvento.id_evento).where(OutboxEvento.id_evento == evento.event_id)
        ).all()
        assert total == []
