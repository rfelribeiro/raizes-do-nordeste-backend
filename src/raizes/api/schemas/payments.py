"""Schemas do pagamento (RF-11, RF-12). Nunca trafegam dados de cartão."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from raizes.api.schemas.common import ApiModel, Money
from raizes.application.payments.request_payment import PaymentOutcome
from raizes.domain.shared.enums import OrderStatus, PaymentAttemptStatus, PaymentMethod


class PaymentRequest(ApiModel):
    method: PaymentMethod = Field(alias="formaPagamento")
    token: str = Field(
        alias="tokenPagamento",
        min_length=1,
        max_length=100,
        description="Token de teste do gateway mock: tok_aprovado, tok_recusado ou tok_timeout.",
        examples=["tok_aprovado"],
    )

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [{"formaPagamento": "PIX", "tokenPagamento": "tok_aprovado"}]
        },
    }


class AttemptOut(ApiModel):
    id: UUID
    attempt_number: int = Field(alias="numeroTentativa")
    method: PaymentMethod = Field(alias="formaPagamento")
    status: PaymentAttemptStatus
    amount: Money = Field(alias="valor", examples=["24.00"])
    refusal_reason: str | None = Field(alias="motivoRecusa")
    gateway_calls: int = Field(alias="qtdChamadasGateway")
    transaction_id: str | None = Field(alias="idTransacaoGateway")
    requested_at: datetime = Field(alias="solicitadoEm")
    responded_at: datetime | None = Field(alias="respondidoEm")


class PaymentResponse(ApiModel):
    attempt: AttemptOut = Field(alias="tentativa")
    order_status: OrderStatus = Field(alias="statusPedido")

    @classmethod
    def from_outcome(cls, outcome: PaymentOutcome) -> PaymentResponse:
        a = outcome.attempt
        return cls(
            attempt=AttemptOut(
                id=a.id,
                attempt_number=a.attempt_number,
                method=a.method,
                status=a.status,
                amount=a.amount,
                refusal_reason=a.refusal_reason,
                gateway_calls=a.gateway_calls,
                transaction_id=a.transaction_id,
                requested_at=a.requested_at,
                responded_at=a.responded_at,
            ),
            order_status=outcome.order_status,
        )
