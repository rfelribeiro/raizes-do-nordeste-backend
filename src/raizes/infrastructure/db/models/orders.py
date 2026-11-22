"""Tabelas `pedidos`, `itens_pedido`, `historico_status_pedido` e `tentativas_pagamento`."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from raizes.infrastructure.db.base import Base


class Order(Base):
    __tablename__ = "pedidos"
    __table_args__ = (
        UniqueConstraint("numero_pedido", name="uq_pedidos_numero_pedido"),
        Index("ix_pedidos_unidade_status_criado", "id_unidade", "status", "criado_em"),
        Index("ix_pedidos_canal_criado", "canal_pedido", "criado_em"),
        Index("ix_pedidos_cliente_criado", "id_cliente", "criado_em"),
        Index(
            "ix_pedidos_expira_em_pendentes",
            "expira_em",
            postgresql_where=text("status = 'AGUARDANDO_PAGAMENTO'"),
        ),
        Index("ix_pedidos_id_usuario_criador", "id_usuario_criador"),
    )

    id: Mapped[uuid.UUID] = mapped_column("id", UUID(as_uuid=True), primary_key=True)
    # Número legível e sequencial, gerado pelo banco (GENERATED ALWAYS AS IDENTITY).
    order_number: Mapped[int] = mapped_column(
        "numero_pedido", BigInteger, Identity(always=True), nullable=False
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        "id_unidade", UUID(as_uuid=True), ForeignKey("unidades.id", ondelete="RESTRICT")
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        "id_cliente", UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="RESTRICT")
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        "id_usuario_criador", UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="RESTRICT")
    )
    channel: Mapped[str] = mapped_column("canal_pedido", String(10), nullable=False)
    status: Mapped[str] = mapped_column("status", String(21), nullable=False)
    items_total: Mapped[Decimal] = mapped_column("valor_itens", Numeric(10, 2), nullable=False)
    discount_total: Mapped[Decimal] = mapped_column(
        "valor_desconto", Numeric(10, 2), nullable=False, server_default=text("0")
    )
    total: Mapped[Decimal] = mapped_column("valor_total", Numeric(10, 2), nullable=False)
    redeemed_points: Mapped[int] = mapped_column(
        "qtd_pontos_resgatados", Integer, nullable=False, server_default=text("0")
    )
    expires_at: Mapped[datetime] = mapped_column(
        "expira_em", DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        "atualizado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", order_by="OrderItem.product_id"
    )


class OrderItem(Base):
    __tablename__ = "itens_pedido"
    __table_args__ = (
        UniqueConstraint("id_pedido", "id_produto", name="uq_itens_pedido_pedido_produto"),
        Index("ix_itens_pedido_id_produto", "id_produto"),
    )

    id: Mapped[uuid.UUID] = mapped_column("id", UUID(as_uuid=True), primary_key=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        "id_pedido", UUID(as_uuid=True), ForeignKey("pedidos.id", ondelete="RESTRICT")
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        "id_produto", UUID(as_uuid=True), ForeignKey("produtos.id", ondelete="RESTRICT")
    )
    quantity: Mapped[int] = mapped_column("qtd_item", Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(
        "valor_preco_unitario", Numeric(10, 2), nullable=False
    )
    line_total: Mapped[Decimal] = mapped_column("valor_total_item", Numeric(10, 2), nullable=False)
    line_discount: Mapped[Decimal] = mapped_column(
        "valor_desconto_item", Numeric(10, 2), nullable=False, server_default=text("0")
    )

    order: Mapped[Order] = relationship(back_populates="items")


class OrderStatusHistory(Base):
    __tablename__ = "historico_status_pedido"
    __table_args__ = (
        Index("ix_historico_status_pedido_pedido_ocorrido", "id_pedido", "ocorrido_em"),
        Index("ix_historico_status_pedido_id_usuario", "id_usuario"),
    )

    id: Mapped[uuid.UUID] = mapped_column("id", UUID(as_uuid=True), primary_key=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        "id_pedido", UUID(as_uuid=True), ForeignKey("pedidos.id", ondelete="RESTRICT")
    )
    previous_status: Mapped[str | None] = mapped_column("status_anterior", String(21))
    new_status: Mapped[str] = mapped_column("status_novo", String(21), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        "id_usuario", UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="RESTRICT")
    )
    reason: Mapped[str | None] = mapped_column("motivo", String(255))
    occurred_at: Mapped[datetime] = mapped_column(
        "ocorrido_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PaymentAttempt(Base):
    __tablename__ = "tentativas_pagamento"
    __table_args__ = (
        UniqueConstraint(
            "id_pedido", "numero_tentativa", name="uq_tentativas_pagamento_pedido_numero"
        ),
        # Impede duas cobranças efetivadas no mesmo pedido, mesmo sob concorrência.
        Index(
            "uq_tentativas_pagamento_pedido_efetivada",
            "id_pedido",
            unique=True,
            postgresql_where=text("status IN ('APROVADO', 'ESTORNADO')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column("id", UUID(as_uuid=True), primary_key=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        "id_pedido", UUID(as_uuid=True), ForeignKey("pedidos.id", ondelete="RESTRICT")
    )
    attempt_number: Mapped[int] = mapped_column("numero_tentativa", Integer, nullable=False)
    gateway_calls: Mapped[int] = mapped_column(
        "qtd_chamadas_gateway", Integer, nullable=False, server_default=text("1")
    )
    method: Mapped[str] = mapped_column("forma_pagamento", String(7), nullable=False)
    status: Mapped[str] = mapped_column("status", String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column("valor", Numeric(10, 2), nullable=False)
    decline_reason: Mapped[str | None] = mapped_column("motivo_recusa", String(255))
    gateway_transaction_id: Mapped[str | None] = mapped_column("id_transacao_gateway", String(80))
    response_payload: Mapped[dict[str, Any] | None] = mapped_column("payload_resposta", JSONB)
    requested_at: Mapped[datetime] = mapped_column(
        "solicitado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    responded_at: Mapped[datetime | None] = mapped_column("respondido_em", DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        "atualizado_em", DateTime(timezone=True), nullable=False, server_default=func.now()
    )
