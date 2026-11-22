"""Porta do gateway de pagamento (o real é externo; aqui, o mock HTTP)."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from raizes.domain.shared.enums import PaymentAttemptStatus, PaymentMethod


@dataclass(frozen=True, slots=True)
class GatewayResult:
    """Resultado de uma cobrança: APROVADO, RECUSADO ou FALHA (timeout esgotado ou conexão).

    `payload` guarda a resposta do gateway e NUNCA dados de cartão. `calls` é a quantidade de
    chamadas feitas (1 a 3).
    """

    status: PaymentAttemptStatus
    calls: int = 1
    transaction_id: str | None = None
    refusal_reason: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


class PaymentGateway(Protocol):
    def charge(
        self, order_id: UUID, amount: Decimal, method: PaymentMethod, token: str
    ) -> GatewayResult: ...
