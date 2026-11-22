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


@dataclass(frozen=True, slots=True)
class AuditRecordView:
    """Registro de auditoria como lido pela consulta (UC-11)."""

    id: UUID
    occurred_at: datetime
    action: str
    resource_type: str
    resource_id: str
    request_id: str
    user_id: UUID | None = None
    role: Role | None = None
    unit_id: UUID | None = None
    channel: OrderChannel | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AuditFilter:
    """Filtros da consulta; o escopo do perfil (unidade do GERENTE) entra por `unit_id`."""

    action: str | None = None
    resource_type: str | None = None
    unit_id: UUID | None = None


class AuditReader(Protocol):
    def search(
        self, filter: AuditFilter, page: int, limit: int
    ) -> tuple[list[AuditRecordView], int]:
        """Página (1-based), do mais recente ao mais antigo, e o total que atende ao filtro."""
        ...
