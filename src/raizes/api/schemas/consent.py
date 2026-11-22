"""Schemas de consentimento (RF-14, LGPD)."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from raizes.api.schemas.common import ApiModel
from raizes.application.consent.consents import ConsentOverview
from raizes.domain.consent.consent import Consent
from raizes.domain.shared.enums import ConsentAction, ConsentPurpose


class ConsentRequest(ApiModel):
    purpose: ConsentPurpose = Field(alias="finalidade")
    action: ConsentAction = Field(alias="acao")
    terms_version: str = Field(alias="versaoTermo", min_length=1, max_length=20, examples=["v1"])

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [{"finalidade": "MARKETING", "acao": "CONCEDIDO", "versaoTermo": "v1"}]
        },
    }


class ConsentOut(ApiModel):
    id: UUID
    purpose: ConsentPurpose = Field(alias="finalidade")
    action: ConsentAction = Field(alias="acao")
    legal_basis: str = Field(alias="baseLegal")
    terms_version: str = Field(alias="versaoTermo")
    recorded_at: datetime = Field(alias="registradoEm")

    @classmethod
    def from_domain(cls, c: Consent) -> ConsentOut:
        return cls(
            id=c.id,
            purpose=c.purpose,
            action=c.action,
            legal_basis=c.legal_basis,
            terms_version=c.terms_version,
            recorded_at=c.recorded_at,
        )


class ConsentListResponse(ApiModel):
    history: list[ConsentOut] = Field(alias="historico")
    current: list[ConsentOut] = Field(
        alias="vigentes", description="Último registro de cada finalidade (CONCEDIDO ou REVOGADO)."
    )

    @classmethod
    def from_overview(cls, overview: ConsentOverview) -> ConsentListResponse:
        return cls(
            history=[ConsentOut.from_domain(c) for c in overview.history],
            current=[ConsentOut.from_domain(c) for c in overview.current.values()],
        )
