"""Tabela `outbox_eventos`: eventos de domínio gravados na mesma transação do negócio."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Identity, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from raizes.infrastructure.db.base import Base


class OutboxEvento(Base):
    __tablename__ = "outbox_eventos"

    id_evento: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tipo_evento: Mapped[str] = mapped_column(Text, nullable=False)
    versao_schema: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo_agregado: Mapped[str] = mapped_column(Text, nullable=False)
    id_agregado: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registrado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Marca d'água estável para a extração incremental (não é a chave primária).
    id_sequencial: Mapped[int] = mapped_column(BigInteger, Identity(always=True), nullable=False)

    __table_args__ = (Index("ix_outbox_eventos_id_sequencial", "id_sequencial"),)
