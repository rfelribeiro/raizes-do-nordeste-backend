"""Implementação SQLAlchemy da porta OutboxWriter."""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from raizes.domain.shared.events import DomainEvent
from raizes.infrastructure.db.models.outbox import OutboxEvento


class SqlAlchemyOutboxWriter:
    """Adiciona os eventos à sessão; commit/rollback ficam com a unidade de trabalho."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, events: Sequence[DomainEvent]) -> None:
        self._session.add_all(
            OutboxEvento(
                id_evento=event.event_id,
                tipo_evento=event.event_type,
                versao_schema=event.schema_version,
                tipo_agregado=event.aggregate_type,
                id_agregado=event.aggregate_id,
                payload=event.payload(),
                ocorrido_em=event.occurred_at,
            )
            for event in events
        )
