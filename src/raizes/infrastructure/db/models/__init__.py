"""Modelos ORM. Importe os módulos aqui para registrá-los no metadata (Alembic)."""

from raizes.infrastructure.db.models.audit import AuditRecord
from raizes.infrastructure.db.models.catalog import Category, MenuItem, Product
from raizes.infrastructure.db.models.consent import Consent
from raizes.infrastructure.db.models.identity import Unit, User
from raizes.infrastructure.db.models.orders import (
    Order,
    OrderItem,
    OrderStatusHistory,
    PaymentAttempt,
)
from raizes.infrastructure.db.models.outbox import OutboxEvent
from raizes.infrastructure.db.models.stock import Stock, StockMovement

__all__ = [
    "AuditRecord",
    "Category",
    "Consent",
    "MenuItem",
    "Order",
    "OrderItem",
    "OrderStatusHistory",
    "OutboxEvent",
    "PaymentAttempt",
    "Product",
    "Stock",
    "StockMovement",
    "Unit",
    "User",
]
