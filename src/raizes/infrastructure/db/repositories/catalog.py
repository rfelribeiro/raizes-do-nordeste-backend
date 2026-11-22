"""Leitura do cardápio e das unidades (portas `MenuRepository` e `UnitRepository`)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from raizes.application.ports.catalog import MenuOffer
from raizes.infrastructure.db.models.catalog import MenuItem, Product
from raizes.infrastructure.db.models.identity import Unit


class SqlAlchemyMenuRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_offers(self, unit_id: UUID, product_ids: list[UUID]) -> dict[UUID, MenuOffer]:
        rows = self._session.execute(
            select(MenuItem, Product)
            .join(Product, Product.id == MenuItem.product_id)
            .where(MenuItem.unit_id == unit_id, MenuItem.product_id.in_(product_ids))
        ).all()
        return {
            item.product_id: MenuOffer(
                product_id=item.product_id,
                unit_id=item.unit_id,
                price=item.local_price if item.local_price is not None else product.reference_price,
                available=item.is_available and product.is_active,
                seasonal_start=item.season_start,
                seasonal_end=item.season_end,
            )
            for item, product in rows
        }

    def existing_product_ids(self, product_ids: list[UUID]) -> set[UUID]:
        return set(self._session.scalars(select(Product.id).where(Product.id.in_(product_ids))))


class SqlAlchemyUnitRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def exists(self, unit_id: UUID) -> bool:
        """Unidade existente e ativa (pré-condição do UC-04)."""
        active = self._session.scalar(select(Unit.is_active).where(Unit.id == unit_id))
        return bool(active)
