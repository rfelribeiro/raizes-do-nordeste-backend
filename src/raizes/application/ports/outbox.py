"""Porta da outbox de eventos de domínio (captura OLTP -> analítico)."""

from collections.abc import Sequence
from typing import Protocol

from raizes.domain.shared.events import DomainEvent


class OutboxWriter(Protocol):
    """Registra eventos na outbox, na MESMA transação do caso de uso.

    A implementação não faz commit: quem controla a transação é o caso de uso (unidade de
    trabalho). Se a transação for desfeita, os eventos também são descartados.
    """

    def add(self, events: Sequence[DomainEvent]) -> None: ...
