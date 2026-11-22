"""Sessão por requisição e unidade de trabalho."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from raizes.application.ports.unit_of_work import UnitOfWork
from raizes.infrastructure.db.session import get_session_factory
from raizes.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


def get_session() -> Iterator[Session]:
    """Uma sessão por requisição: desfaz o que não foi confirmado e fecha ao fim."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        try:
            session.rollback()  # no-op se o caso de uso já fez commit
        finally:
            session.close()


def get_unit_of_work(session: Annotated[Session, Depends(get_session)]) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session)
