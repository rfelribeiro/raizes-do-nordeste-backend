"""Eventos de domínio do pedido e do pagamento. Payload sem PII: só ids, valores, canal e status."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from raizes.domain.shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class OrderCreated(DomainEvent):
    event_type = "pedido_criado"

    unit_id: UUID
    customer_id: UUID | None
    channel: str
    status: str
    total: Decimal

    def payload(self) -> dict[str, Any]:
        return {
            "unidade_id": str(self.unit_id),
            "cliente_id": str(self.customer_id) if self.customer_id else None,
            "canal_pedido": self.channel,
            "status": self.status,
            "valor_total": str(self.total),
        }


@dataclass(frozen=True, kw_only=True)
class OrderStatusChanged(DomainEvent):
    event_type = "status_pedido_alterado"

    unit_id: UUID
    channel: str
    previous_status: str
    new_status: str

    def payload(self) -> dict[str, Any]:
        return {
            "unidade_id": str(self.unit_id),
            "canal_pedido": self.channel,
            "status_anterior": self.previous_status,
            "status_novo": self.new_status,
        }


@dataclass(frozen=True, kw_only=True)
class PaymentApproved(DomainEvent):
    event_type = "pagamento_aprovado"

    unit_id: UUID
    channel: str
    method: str
    amount: Decimal
    attempt_number: int

    def payload(self) -> dict[str, Any]:
        return {
            "unidade_id": str(self.unit_id),
            "canal_pedido": self.channel,
            "forma_pagamento": self.method,
            "valor": str(self.amount),
            "numero_tentativa": self.attempt_number,
        }


@dataclass(frozen=True, kw_only=True)
class PaymentRefused(DomainEvent):
    event_type = "pagamento_recusado"

    unit_id: UUID
    channel: str
    method: str
    amount: Decimal
    attempt_number: int
    reason: str

    def payload(self) -> dict[str, Any]:
        return {
            "unidade_id": str(self.unit_id),
            "canal_pedido": self.channel,
            "forma_pagamento": self.method,
            "valor": str(self.amount),
            "numero_tentativa": self.attempt_number,
            "motivo": self.reason,
        }
