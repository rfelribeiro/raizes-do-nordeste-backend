"""Implementação SQLAlchemy da porta OutboxWriter."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from raizes.domain.shared.events import DomainEvent
from raizes.infrastructure.db.models.outbox import OutboxEvent


class SqlAlchemyOutboxWriter:
    """Adiciona os eventos à sessão; commit/rollback ficam com a unidade de trabalho."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, events: Sequence[DomainEvent]) -> None:
        self._session.add_all(
            OutboxEvent(
                event_id=event.event_id,
                event_type=event.event_type,
                schema_version=event.schema_version,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                payload=event.payload(),
                occurred_at=event.occurred_at,
            )
            for event in events
        )
