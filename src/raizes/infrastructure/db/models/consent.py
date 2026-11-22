"""Tabela `consentimentos` (histórico append-only de concessões e revogações, LGPD)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from raizes.infrastructure.db.base import Base


class Consent(Base):
    __tablename__ = "consentimentos"
    __table_args__ = (
        Index(
            "ix_consentimentos_vigente",
            "id_usuario",
            "finalidade",
            text("registrado_em DESC"),
            postgresql_include=["acao"],
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column("id", UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        "id_usuario", UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="RESTRICT")
    )
    purpose: Mapped[str] = mapped_column("finalidade", String(15), nullable=False)
    action: Mapped[str] = mapped_column("acao", String(9), nullable=False)
    legal_basis: Mapped[str] = mapped_column("base_legal", String(60), nullable=False)
    terms_version: Mapped[str] = mapped_column("versao_termo", String(20), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        "registrado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
