"""Persistência dos consentimentos (append-only)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from raizes.domain.consent.consent import Consent
from raizes.domain.shared.enums import ConsentAction, ConsentPurpose
from raizes.infrastructure.db.models.consent import Consent as ConsentModel


class SqlAlchemyConsentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def history(self, user_id: UUID) -> list[Consent]:
        rows = self._session.scalars(
            select(ConsentModel)
            .where(ConsentModel.user_id == user_id)
            .order_by(ConsentModel.recorded_at, ConsentModel.id)
        ).all()
        return [
            Consent(
                id=r.id,
                user_id=r.user_id,
                purpose=ConsentPurpose(r.purpose),
                action=ConsentAction(r.action),
                terms_version=r.terms_version,
                legal_basis=r.legal_basis,
                recorded_at=r.recorded_at,
            )
            for r in rows
        ]

    def add(self, consent: Consent) -> None:
        self._session.add(
            ConsentModel(
                id=consent.id,
                user_id=consent.user_id,
                purpose=consent.purpose.value,
                action=consent.action.value,
                legal_basis=consent.legal_basis,
                terms_version=consent.terms_version,
                recorded_at=consent.recorded_at,
            )
        )
