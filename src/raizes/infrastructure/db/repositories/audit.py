"""Auditoria: gravação na transação do caso de uso (UC-24) e consulta paginada (UC-11)."""

from typing import Any
from uuid import uuid4

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from raizes.application.ports.audit import AuditEntry, AuditFilter, AuditRecordView
from raizes.domain.shared.enums import OrderChannel, Role
from raizes.infrastructure.db.models.audit import AuditRecord
from raizes.infrastructure.logging import request_id_var


class SqlAlchemyAuditRecorder:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(self, entry: AuditEntry) -> None:
        extra: dict[str, Any] = {"occurred_at": entry.occurred_at} if entry.occurred_at else {}
        self._session.add(
            AuditRecord(
                id=uuid4(),
                user_id=entry.user_id,
                role=entry.role.value if entry.role else None,
                action=entry.action,
                resource_type=entry.resource_type,
                resource_id=entry.resource_id,
                unit_id=entry.unit_id,
                order_channel=entry.channel.value if entry.channel else None,
                request_id=request_id_var.get() or "sem-requisicao",
                details=entry.details,
                **extra,
            )
        )


class SqlAlchemyAuditReader:
    def __init__(self, session: Session) -> None:
        self._session = session

    def search(
        self, filter: AuditFilter, page: int, limit: int
    ) -> tuple[list[AuditRecordView], int]:
        conditions: list[ColumnElement[bool]] = []
        if filter.action is not None:
            conditions.append(AuditRecord.action == filter.action)
        if filter.resource_type is not None:
            conditions.append(AuditRecord.resource_type == filter.resource_type)
        if filter.unit_id is not None:
            conditions.append(AuditRecord.unit_id == filter.unit_id)
        total = (
            self._session.scalar(select(func.count()).select_from(AuditRecord).where(*conditions))
            or 0
        )
        rows = self._session.scalars(
            select(AuditRecord)
            .where(*conditions)
            .order_by(AuditRecord.occurred_at.desc(), AuditRecord.id)
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
        views = [
            AuditRecordView(
                id=r.id,
                occurred_at=r.occurred_at,
                action=r.action,
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                request_id=r.request_id,
                user_id=r.user_id,
                role=Role(r.role) if r.role else None,
                unit_id=r.unit_id,
                channel=OrderChannel(r.order_channel) if r.order_channel else None,
                details=r.details,
            )
            for r in rows
        ]
        return views, total
