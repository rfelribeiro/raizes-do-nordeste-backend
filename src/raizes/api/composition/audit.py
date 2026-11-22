"""Composição do módulo de auditoria."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from raizes.api.composition.db import get_session
from raizes.application.audit.query_audit import QueryAudit
from raizes.infrastructure.db.repositories.audit import SqlAlchemyAuditReader


def get_query_audit(session: Annotated[Session, Depends(get_session)]) -> QueryAudit:
    return QueryAudit(SqlAlchemyAuditReader(session))
