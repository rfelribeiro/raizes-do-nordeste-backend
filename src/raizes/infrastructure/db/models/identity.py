"""Tabelas `unidades` e `usuarios` (identidade e lotação).

Modelos de persistência (data mapper), não o domínio. Atributos em inglês, colunas em português
(ADR 0010). Os CHECKs vivem na migração (fonte de verdade do esquema), não aqui.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CHAR,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from raizes.infrastructure.db.base import Base


class Unit(Base):
    __tablename__ = "unidades"
    __table_args__ = (UniqueConstraint("codigo", name="uq_unidades_codigo"),)

    id: Mapped[uuid.UUID] = mapped_column("id", UUID(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column("codigo", String(20), nullable=False)
    name: Mapped[str] = mapped_column("nome", String(120), nullable=False)
    city: Mapped[str] = mapped_column("cidade", String(80), nullable=False)
    state: Mapped[str] = mapped_column("uf", CHAR(2), nullable=False)
    format: Mapped[str] = mapped_column("formato", String(10), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        "eh_ativa", Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        "atualizado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class User(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        Index("uq_usuarios_email_lower", text("lower(email)"), unique=True),
        Index("ix_usuarios_id_unidade_lotacao", "id_unidade_lotacao"),
    )

    id: Mapped[uuid.UUID] = mapped_column("id", UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column("nome", String(120), nullable=False)
    email: Mapped[str] = mapped_column("email", String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column("senha_hash", String(255), nullable=False)
    role: Mapped[str] = mapped_column("perfil", String(10), nullable=False)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        "id_unidade_lotacao", UUID(as_uuid=True), ForeignKey("unidades.id", ondelete="RESTRICT")
    )
    birth_date: Mapped[date | None] = mapped_column("data_nascimento", Date)
    is_active: Mapped[bool] = mapped_column(
        "eh_ativo", Boolean, nullable=False, server_default=text("true")
    )
    anonymized_at: Mapped[datetime | None] = mapped_column(
        "anonimizado_em", DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        "atualizado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
