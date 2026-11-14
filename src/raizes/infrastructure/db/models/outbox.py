"""Tabela `outbox_eventos`: eventos de domínio gravados na mesma transação do negócio.

Os atributos Python seguem em inglês (convenção de código); os nomes das colunas no banco são
em português (ADR 0010).
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Identity, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from raizes.infrastructure.db.base import Base


class OutboxEvent(Base):
    __tablename__ = "outbox_eventos"

    event_id: Mapped[uuid.UUID] = mapped_column("id_evento", UUID(as_uuid=True), primary_key=True)
    event_type: Mapped[str] = mapped_column("tipo_evento", Text, nullable=False)
    schema_version: Mapped[int] = mapped_column("versao_schema", Integer, nullable=False)
    aggregate_type: Mapped[str] = mapped_column("tipo_agregado", Text, nullable=False)
    aggregate_id: Mapped[str] = mapped_column("id_agregado", Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        "ocorrido_em", DateTime(timezone=True), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        "registrado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Marca d'água estável para a extração incremental (não é a chave primária).
    sequence_id: Mapped[int] = mapped_column(
        "id_sequencial", BigInteger, Identity(always=True), nullable=False
    )

    __table_args__ = (Index("ix_outbox_eventos_id_sequencial", "id_sequencial"),)
