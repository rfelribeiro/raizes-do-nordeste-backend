"""Composição do módulo de pedidos."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from raizes.api.composition.db import get_session
from raizes.application.orders.create_order import CreateOrder
from raizes.application.orders.queries import GetOrder, ListOrders
from raizes.application.orders.update_status import UpdateOrderStatus
from raizes.infrastructure.db.outbox import SqlAlchemyOutboxWriter
from raizes.infrastructure.db.repositories.audit import SqlAlchemyAuditRecorder
from raizes.infrastructure.db.repositories.catalog import (
    SqlAlchemyMenuRepository,
    SqlAlchemyUnitRepository,
)
from raizes.infrastructure.db.repositories.identity import SqlAlchemyUserRepository
from raizes.infrastructure.db.repositories.orders import SqlAlchemyOrderRepository
from raizes.infrastructure.db.repositories.stock import SqlAlchemyStockRepository
from raizes.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

SessionDep = Annotated[Session, Depends(get_session)]


def get_create_order(session: SessionDep) -> CreateOrder:
    return CreateOrder(
        orders=SqlAlchemyOrderRepository(session),
        menu=SqlAlchemyMenuRepository(session),
        units=SqlAlchemyUnitRepository(session),
        users=SqlAlchemyUserRepository(session),
        stock=SqlAlchemyStockRepository(session),
        audit=SqlAlchemyAuditRecorder(session),
        outbox=SqlAlchemyOutboxWriter(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


def get_list_orders(session: SessionDep) -> ListOrders:
    return ListOrders(SqlAlchemyOrderRepository(session))


def get_get_order(session: SessionDep) -> GetOrder:
    return GetOrder(SqlAlchemyOrderRepository(session))


def get_update_order_status(session: SessionDep) -> UpdateOrderStatus:
    return UpdateOrderStatus(
        orders=SqlAlchemyOrderRepository(session),
        audit=SqlAlchemyAuditRecorder(session),
        outbox=SqlAlchemyOutboxWriter(session),
        uow=SqlAlchemyUnitOfWork(session),
    )
