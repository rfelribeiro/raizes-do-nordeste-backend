"""Persistência do estoque: saldo com bloqueio de linha (RNF-11) e razão append-only."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from raizes.domain.stock.stock import Stock, StockMovement
from raizes.infrastructure.db.models import stock as models


class SqlAlchemyStockRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_update(self, unit_id: UUID, product_ids: list[UUID]) -> dict[UUID, Stock]:
        """SELECT ... FOR UPDATE ordenado por `id_produto`: ordem global, sem deadlock."""
        rows = self._session.scalars(
            select(models.Stock)
            .where(models.Stock.unit_id == unit_id, models.Stock.product_id.in_(product_ids))
            .order_by(models.Stock.product_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).all()
        return {
            row.product_id: Stock(
                unit_id=row.unit_id,
                product_id=row.product_id,
                available=row.available_qty,
                reserved=row.reserved_qty,
            )
            for row in rows
        }

    def save(self, stock: Stock, movements: Sequence[StockMovement]) -> None:
        row = self._session.get(models.Stock, (stock.unit_id, stock.product_id))
        if row is None:
            raise LookupError("estoque inexistente: carregue com get_for_update antes de salvar")
        row.available_qty = stock.available
        row.reserved_qty = stock.reserved
        row.updated_at = func.now()
        self._session.add_all(
            models.StockMovement(
                id=m.id,
                unit_id=m.unit_id,
                product_id=m.product_id,
                type=m.type.value,
                moved_qty=m.quantity,
                order_id=m.order_id,
                user_id=m.user_id,
                reason=m.reason,
                occurred_at=m.occurred_at,
            )
            for m in movements
        )
