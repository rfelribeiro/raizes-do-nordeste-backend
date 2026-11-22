"""Composição do módulo de consentimento."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from raizes.api.composition.db import get_session
from raizes.application.consent.consents import ListConsents, RegisterConsent
from raizes.infrastructure.db.repositories.audit import SqlAlchemyAuditRecorder
from raizes.infrastructure.db.repositories.consent import SqlAlchemyConsentRepository
from raizes.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


def get_register_consent(session: Annotated[Session, Depends(get_session)]) -> RegisterConsent:
    return RegisterConsent(
        SqlAlchemyConsentRepository(session),
        SqlAlchemyAuditRecorder(session),
        SqlAlchemyUnitOfWork(session),
    )


def get_list_consents(session: Annotated[Session, Depends(get_session)]) -> ListConsents:
    return ListConsents(SqlAlchemyConsentRepository(session))
