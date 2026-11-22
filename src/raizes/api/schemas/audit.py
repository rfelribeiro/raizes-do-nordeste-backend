"""Schemas da consulta de auditoria (RF-13). `detalhes` nunca traz dados pessoais."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from raizes.api.schemas.common import ApiModel
from raizes.application.ports.audit import AuditRecordView
from raizes.domain.shared.enums import OrderChannel, Role


class AuditOut(ApiModel):
    id: UUID
    occurred_at: datetime = Field(alias="ocorridoEm")
    user_id: UUID | None = Field(alias="usuarioId")
    role: Role | None = Field(alias="perfil")
    action: str = Field(alias="acao", examples=["PEDIDO_CRIADO"])
    resource_type: str = Field(alias="tipoRecurso", examples=["PEDIDO"])
    resource_id: str = Field(alias="idRecurso")
    unit_id: UUID | None = Field(alias="unidadeId")
    channel: OrderChannel | None = Field(alias="canalPedido")
    request_id: str = Field(alias="idRequisicao")
    details: dict[str, Any] = Field(alias="detalhes")

    @classmethod
    def from_view(cls, v: AuditRecordView) -> AuditOut:
        return cls(
            id=v.id,
            occurred_at=v.occurred_at,
            user_id=v.user_id,
            role=v.role,
            action=v.action,
            resource_type=v.resource_type,
            resource_id=v.resource_id,
            unit_id=v.unit_id,
            channel=v.channel,
            request_id=v.request_id,
            details=v.details,
        )
