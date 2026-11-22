"""Tabela `auditoria` (trilha append-only de ações sensíveis; sem PII em `detalhes`)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from raizes.infrastructure.db.base import Base


class AuditRecord(Base):
    __tablename__ = "auditoria"
    __table_args__ = (
        Index("ix_auditoria_ocorrido_em", "ocorrido_em"),
        Index("ix_auditoria_unidade_ocorrido", "id_unidade", "ocorrido_em"),
        Index("ix_auditoria_recurso", "tipo_recurso", "id_recurso"),
        Index("ix_auditoria_id_requisicao", "id_requisicao"),
        Index("ix_auditoria_id_usuario", "id_usuario"),
    )

    id: Mapped[uuid.UUID] = mapped_column("id", UUID(as_uuid=True), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        "ocorrido_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        "id_usuario", UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="RESTRICT")
    )
    role: Mapped[str | None] = mapped_column("perfil", String(10))
    action: Mapped[str] = mapped_column("acao", String(40), nullable=False)
    resource_type: Mapped[str] = mapped_column("tipo_recurso", String(30), nullable=False)
    resource_id: Mapped[str] = mapped_column("id_recurso", String(64), nullable=False)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        "id_unidade", UUID(as_uuid=True), ForeignKey("unidades.id", ondelete="RESTRICT")
    )
    order_channel: Mapped[str | None] = mapped_column("canal_pedido", String(10))
    request_id: Mapped[str] = mapped_column("id_requisicao", String(64), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        "detalhes", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
