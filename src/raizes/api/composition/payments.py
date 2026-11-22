"""Composição do módulo de pagamentos. O gateway é trocável nos testes (dependency_overrides)."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from raizes.api.composition.db import get_session
from raizes.application.payments.request_payment import RequestPayment
from raizes.application.ports.payment_gateway import PaymentGateway
from raizes.infrastructure.config import get_settings
from raizes.infrastructure.db.outbox import SqlAlchemyOutboxWriter
from raizes.infrastructure.db.repositories.audit import SqlAlchemyAuditRecorder
from raizes.infrastructure.db.repositories.orders import SqlAlchemyOrderRepository
from raizes.infrastructure.db.repositories.stock import SqlAlchemyStockRepository
from raizes.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from raizes.infrastructure.payment.http_gateway import HttpPaymentGateway


@lru_cache
def get_payment_gateway() -> PaymentGateway:
    settings = get_settings()
    return HttpPaymentGateway(
        settings.payment_gateway_url,
        timeout_seconds=settings.payment_timeout_seconds,
        max_retries=settings.payment_max_retries,
    )


def get_request_payment(
    session: Annotated[Session, Depends(get_session)],
    gateway: Annotated[PaymentGateway, Depends(get_payment_gateway)],
) -> RequestPayment:
    return RequestPayment(
        orders=SqlAlchemyOrderRepository(session),
        stock=SqlAlchemyStockRepository(session),
        gateway=gateway,
        audit=SqlAlchemyAuditRecorder(session),
        outbox=SqlAlchemyOutboxWriter(session),
        uow=SqlAlchemyUnitOfWork(session),
    )
