"""Tabelas `categorias`, `produtos` e `itens_cardapio` (catálogo da rede e cardápio da unidade)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from raizes.infrastructure.db.base import Base


class Category(Base):
    __tablename__ = "categorias"
    __table_args__ = (UniqueConstraint("nome", name="uq_categorias_nome"),)

    id: Mapped[uuid.UUID] = mapped_column("id", UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column("nome", String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        "atualizado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Product(Base):
    __tablename__ = "produtos"
    __table_args__ = (Index("ix_produtos_id_categoria", "id_categoria"),)

    id: Mapped[uuid.UUID] = mapped_column("id", UUID(as_uuid=True), primary_key=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        "id_categoria", UUID(as_uuid=True), ForeignKey("categorias.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column("nome", String(120), nullable=False)
    description: Mapped[str | None] = mapped_column("descricao", String(500))
    reference_price: Mapped[Decimal] = mapped_column(
        "valor_preco_referencia", Numeric(10, 2), nullable=False
    )
    is_seasonal: Mapped[bool] = mapped_column(
        "eh_sazonal", Boolean, nullable=False, server_default=text("false")
    )
    is_active: Mapped[bool] = mapped_column(
        "eh_ativo", Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        "atualizado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MenuItem(Base):
    __tablename__ = "itens_cardapio"
    __table_args__ = (
        UniqueConstraint("id_unidade", "id_produto", name="uq_itens_cardapio_unidade_produto"),
        Index("ix_itens_cardapio_id_produto", "id_produto"),
    )

    id: Mapped[uuid.UUID] = mapped_column("id", UUID(as_uuid=True), primary_key=True)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        "id_unidade", UUID(as_uuid=True), ForeignKey("unidades.id", ondelete="RESTRICT")
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        "id_produto", UUID(as_uuid=True), ForeignKey("produtos.id", ondelete="RESTRICT")
    )
    is_available: Mapped[bool] = mapped_column(
        "eh_disponivel", Boolean, nullable=False, server_default=text("true")
    )
    local_price: Mapped[Decimal | None] = mapped_column("valor_preco_local", Numeric(10, 2))
    season_start: Mapped[date | None] = mapped_column("data_inicio_sazonal", Date)
    season_end: Mapped[date | None] = mapped_column("data_fim_sazonal", Date)
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        "atualizado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
