from dataclasses import dataclass
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from raizes.domain.shared.events import DomainEvent
from raizes.infrastructure.db.models.outbox import OutboxEvent
from raizes.infrastructure.db.outbox import SqlAlchemyOutboxWriter
from raizes.infrastructure.db.session import get_engine

pytestmark = pytest.mark.integration


@dataclass(frozen=True, kw_only=True)
class FakeEvent(DomainEvent):
    event_type = "evento_falso"
    value: int = 0

    def payload(self) -> dict[str, Any]:
        return {"value": self.value}


def _event(value: int = 1) -> FakeEvent:
    return FakeEvent(aggregate_type="teste", aggregate_id="a-1", value=value)


def test_writes_and_reads_event_in_same_transaction() -> None:
    event = _event(5)
    # A transação externa nunca é confirmada: nada fica gravado no banco após o teste.
    with get_engine().connect() as connection, connection.begin() as transaction:
        with Session(bind=connection) as session:
            SqlAlchemyOutboxWriter(session).add([event])
            session.flush()
            row = session.scalars(
                select(OutboxEvent).where(OutboxEvent.event_id == event.event_id)
            ).one()
            assert row.event_type == "evento_falso"
            assert row.payload == {"value": 5}
            assert row.schema_version == 1
            assert row.occurred_at == event.occurred_at
            assert row.recorded_at is not None
            assert row.sequence_id > 0
        transaction.rollback()


def test_rollback_discards_event() -> None:
    event = _event()
    with get_engine().connect() as connection:
        with Session(bind=connection) as session:
            SqlAlchemyOutboxWriter(session).add([event])
            session.flush()
            session.rollback()
        found = connection.execute(
            select(OutboxEvent.event_id).where(OutboxEvent.event_id == event.event_id)
        ).all()
        assert found == []
