"""Tabelas `estoques` (saldo) e `movimentacoes_estoque` (razão append-only)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from raizes.infrastructure.db.base import Base


class Stock(Base):
    __tablename__ = "estoques"
    __table_args__ = (Index("ix_estoques_id_produto", "id_produto"),)

    unit_id: Mapped[uuid.UUID] = mapped_column(
        "id_unidade",
        UUID(as_uuid=True),
        ForeignKey("unidades.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        "id_produto",
        UUID(as_uuid=True),
        ForeignKey("produtos.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    available_qty: Mapped[int] = mapped_column("qtd_disponivel", Integer, nullable=False)
    reserved_qty: Mapped[int] = mapped_column("qtd_reservada", Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        "atualizado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StockMovement(Base):
    __tablename__ = "movimentacoes_estoque"
    __table_args__ = (
        Index(
            "ix_movimentacoes_estoque_unidade_produto_ocorrido",
            "id_unidade",
            "id_produto",
            "ocorrido_em",
        ),
        Index("ix_movimentacoes_estoque_id_pedido", "id_pedido"),
        Index("ix_movimentacoes_estoque_id_usuario", "id_usuario"),
    )

    id: Mapped[uuid.UUID] = mapped_column("id", UUID(as_uuid=True), primary_key=True)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        "id_unidade", UUID(as_uuid=True), ForeignKey("unidades.id", ondelete="RESTRICT")
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        "id_produto", UUID(as_uuid=True), ForeignKey("produtos.id", ondelete="RESTRICT")
    )
    type: Mapped[str] = mapped_column("tipo", String(16), nullable=False)
    moved_qty: Mapped[int] = mapped_column("qtd_movimentada", Integer, nullable=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        "id_pedido", UUID(as_uuid=True), ForeignKey("pedidos.id", ondelete="RESTRICT")
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        "id_usuario", UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="RESTRICT")
    )
    reason: Mapped[str | None] = mapped_column("motivo", String(255))
    occurred_at: Mapped[datetime] = mapped_column(
        "ocorrido_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
