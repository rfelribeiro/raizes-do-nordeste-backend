"""Portas de leitura do catálogo e das unidades."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MenuOffer:
    """Oferta de um produto no cardápio da unidade, com o preço efetivo (RN-10)."""

    product_id: UUID
    unit_id: UUID
    price: Decimal  # preço local se existir, senão o de referência
    available: bool
    seasonal_start: date | None = None
    seasonal_end: date | None = None

    def is_orderable(self, today: date) -> bool:
        """RN-12: disponível e dentro do período sazonal, quando houver."""
        if not self.available:
            return False
        if self.seasonal_start is not None and today < self.seasonal_start:
            return False
        return not (self.seasonal_end is not None and today > self.seasonal_end)


class MenuRepository(Protocol):
    def get_offers(self, unit_id: UUID, product_ids: list[UUID]) -> dict[UUID, MenuOffer]:
        """Ofertas encontradas; produto fora do cardápio da unidade fica ausente do dict."""
        ...


class UnitRepository(Protocol):
    def exists(self, unit_id: UUID) -> bool: ...
