"""POST /pedidos/{id}/pagamentos (UC-05)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from raizes.api.composition.payments import get_request_payment
from raizes.api.schemas.payments import PaymentRequest, PaymentResponse
from raizes.api.security import require_roles
from raizes.api.v1.docs import E401, E403, E404, E409_PAGAMENTO, E422, E504, erros
from raizes.application.payments.request_payment import RequestPayment
from raizes.application.principal import Principal
from raizes.domain.shared.enums import Role

router = APIRouter(prefix="/pedidos", tags=["Pagamentos"])


@router.post(
    "/{order_id}/pagamentos",
    status_code=201,
    summary="Solicita o pagamento do pedido ao gateway mock",
    description=(
        "Aprovado: pedido PAGO e estoque baixado. Recusado: responde 201 com a tentativa "
        "RECUSADO e o pedido continua em AGUARDANDO_PAGAMENTO. "
        "Timeout (3 s, 2 novas chamadas): 504."
    ),
    responses=erros(E401, E403, E404, E409_PAGAMENTO, E422, E504),
)
def request_payment(
    order_id: UUID,
    body: PaymentRequest,
    principal: Annotated[Principal, Depends(require_roles(Role.CLIENTE))],
    use_case: Annotated[RequestPayment, Depends(get_request_payment)],
) -> PaymentResponse:
    outcome = use_case.execute(principal, order_id, body.method, body.token)
    return PaymentResponse.from_outcome(outcome)
