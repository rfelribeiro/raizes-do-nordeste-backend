"""Porta de auditoria (tabela `auditoria`); o adaptador preenche `id` e `requestId`."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from raizes.domain.shared.enums import OrderChannel, Role


@dataclass(frozen=True, slots=True)
class AuditEntry:
    action: str
    resource_type: str
    resource_id: str
    user_id: UUID | None = None
    role: Role | None = None  # nulo se, e somente se, user_id for nulo (CHECK do DER)
    unit_id: UUID | None = None
    channel: OrderChannel | None = None
    details: dict[str, Any] = field(default_factory=dict)  # sem PII
    occurred_at: datetime | None = None  # None: o banco usa now()


class AuditRecorder(Protocol):
    """Registra na MESMA transação do caso de uso; nunca faz commit."""

    def record(self, entry: AuditEntry) -> None: ...
