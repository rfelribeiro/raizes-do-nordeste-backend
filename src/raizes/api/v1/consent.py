"""Rotas de consentimento (UC-09, LGPD)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from raizes.api.composition.consent import get_list_consents, get_register_consent
from raizes.api.schemas.consent import ConsentListResponse, ConsentOut, ConsentRequest
from raizes.api.security import require_roles
from raizes.api.v1.docs import E401, E403, E409_CONSENTIMENTO, E422, erros
from raizes.application.consent.consents import ListConsents, RegisterConsent
from raizes.application.principal import Principal
from raizes.domain.shared.enums import Role

router = APIRouter(prefix="/consentimentos", tags=["Consentimentos"])


@router.post(
    "",
    status_code=201,
    summary="Registra a concessão ou a revogação de um consentimento",
    description="Append-only: cada chamada grava um novo registro; o vigente é o último.",
    responses=erros(E401, E403, E409_CONSENTIMENTO, E422),
)
def register_consent(
    body: ConsentRequest,
    principal: Annotated[Principal, Depends(require_roles(Role.CLIENTE))],
    use_case: Annotated[RegisterConsent, Depends(get_register_consent)],
) -> ConsentOut:
    consent = use_case.execute(principal, body.purpose, body.action, body.terms_version)
    return ConsentOut.from_domain(consent)


@router.get(
    "",
    summary="Lista os próprios consentimentos e o vigente por finalidade",
    responses=erros(E401, E403),
)
def list_consents(
    principal: Annotated[Principal, Depends(require_roles(Role.CLIENTE))],
    use_case: Annotated[ListConsents, Depends(get_list_consents)],
) -> ConsentListResponse:
    return ConsentListResponse.from_overview(use_case.execute(principal))
